package com.appiansupport.mat;

import java.io.File;
import java.io.PrintStream;
import java.util.*;
import org.eclipse.equinox.app.IApplication;
import org.eclipse.equinox.app.IApplicationContext;
import org.eclipse.mat.query.*;
import org.eclipse.mat.snapshot.*;
import org.eclipse.mat.snapshot.model.*;
import org.eclipse.mat.snapshot.query.SnapshotQuery;
import org.eclipse.mat.util.ConsoleProgressListener;

/** Non-interactive, bounded JSON interface. No network or process execution. */
public final class AgentApplication implements IApplication {
  private static final String HELP = "mat-cli <info|histogram|dominators|object|references|gc-roots|threads|oql|query> <heap.hprof> [value] [--limit N] [--offset N]\n"
      + "object/references/gc-roots: value is hexadecimal address (0x...).\n"
      + "oql/query: value is one quoted MAT expression. references defaults to outgoing; add --incoming.\n"
      + "JSON on stdout; progress/errors on stderr. Exit: 0 success, 2 usage, 1 analysis failure.\n"
      + "Use mat-cli legacy <heap.hprof> -c for the original interactive CLI.";

  @Override public Object start(IApplicationContext context) {
    return run((String[]) context.getArguments().get("application.args"));
  }
  int run(String[] args) {
    PrintStream output = System.out;
    if (args.length == 0 || Arrays.asList(args).contains("--help")) {
      output.println(HELP); return 0;
    }
    ISnapshot snapshot = null;
    // Some MAT queries print diagnostics directly; keep stdout exclusively for the envelope.
    System.setOut(System.err);
    try {
      Set<String> commands = Set.of("info", "histogram", "dominators", "object", "references", "gc-roots", "threads", "oql", "query");
      if (args.length < 2 || !commands.contains(args[0])) throw new IllegalArgumentException(HELP);
      String command = args[0];
      int limit = 100, offset = 0;
      boolean incoming = false;
      String value = null;
      for (int i = 2; i < args.length; i++) {
        switch (args[i]) {
          case "--limit": if (++i == args.length) throw new IllegalArgumentException("Missing limit"); limit = Integer.parseInt(args[i]); break;
          case "--offset": if (++i == args.length) throw new IllegalArgumentException("Missing offset"); offset = Integer.parseInt(args[i]); break;
          case "--incoming": incoming = true; break;
          default: if (value != null || args[i].startsWith("--")) throw new IllegalArgumentException("Unexpected argument: " + args[i]); value = args[i];
        }
      }
      if (limit < 1 || limit > 10000 || offset < 0) throw new IllegalArgumentException("limit must be 1..10000; offset must be >= 0");
      if (Set.of("object", "references", "gc-roots", "oql", "query").contains(command) && value == null) throw new IllegalArgumentException("Missing value for " + command);
      File heap = new File(args[1]);
      if (!heap.isFile()) throw new IllegalArgumentException("Heap dump does not exist: " + heap);
      var listener = new ConsoleProgressListener(System.err);
      snapshot = SnapshotFactory.openSnapshot(heap, listener);
      Object result;
      switch (command) {
        case "info":
          var info = snapshot.getSnapshotInfo();
          result = Map.of("objects", info.getNumberOfObjects(), "classes", info.getNumberOfClasses(), "usedHeapBytes", info.getUsedHeapSize(), "jvm", String.valueOf(info.getJvmInfo())); break;
        case "object": result = describe(snapshot.getObject(address(snapshot, value))); break;
        case "references":
          int id = address(snapshot, value);
          int[] ids = incoming ? snapshot.getInboundRefererIds(id) : snapshot.getOutboundReferentIds(id);
          result = objects(snapshot, ids, offset, limit); break;
        case "gc-roots":
          int[] path = snapshot.getPathsFromGCRoots(address(snapshot, value), null).getNextShortestPath();
          result = objects(snapshot, path == null ? new int[0] : path, offset, limit); break;
        case "dominators": result = objects(snapshot, snapshot.getImmediateDominatedIds(-1), offset, limit); break;
        case "histogram":
          var records = new ArrayList<>(snapshot.getHistogram(listener).getClassHistogramRecords());
          records.sort(Comparator.comparingLong(ClassHistogramRecord::getUsedHeapSize).reversed().thenComparing(ClassHistogramRecord::getLabel));
          var rows = new ArrayList<Object>();
          for (int i = offset; i < records.size() && rows.size() < limit; i++) {
            var r = records.get(i); rows.add(Map.of("class", r.getLabel(), "objects", r.getNumberOfObjects(), "shallowBytes", r.getUsedHeapSize()));
          }
          result = page(rows, records.size(), offset, limit); break;
        default:
          Object queryResult = command.equals("oql") ? SnapshotFactory.createQuery(value).execute(snapshot, listener)
              : SnapshotQuery.parse(command.equals("threads") ? "thread_overview" : value, snapshot).execute(listener);
          result = queryResult(snapshot, queryResult, offset, limit);
      }
      output.println(json(Map.of("ok", true, "command", command, "result", result)));
      return 0;
    } catch (IllegalArgumentException e) {
      output.println(json(Map.of("ok", false, "error", String.valueOf(e.getMessage())))); return 2;
    } catch (Exception e) {
      System.err.println(e);
      output.println(json(Map.of("ok", false, "error", String.valueOf(e.getMessage())))); return 1;
    } finally {
      if (snapshot != null) SnapshotFactory.dispose(snapshot);
      System.setOut(output);
    }
  }
  private static int address(ISnapshot s, String value) throws Exception {
    if (!value.matches("0[xX][0-9a-fA-F]+")) throw new IllegalArgumentException("Expected hexadecimal address with 0x prefix");
    return s.mapAddressToId(Long.parseUnsignedLong(value.substring(2), 16));
  }
  private static Map<String,Object> describe(IObject o) {
    Map<String,Object> row = new LinkedHashMap<>();
    row.put("id", o.getObjectId()); row.put("address", "0x" + Long.toHexString(o.getObjectAddress()));
    row.put("class", o.getClazz().getName()); row.put("name", o.getDisplayName());
    row.put("shallowBytes", o.getUsedHeapSize()); row.put("retainedBytes", o.getRetainedHeapSize());
    return row;
  }
  private static Object objects(ISnapshot s, int[] ids, int offset, int limit) throws Exception {
    var rows = new ArrayList<Object>();
    for (int i = offset; i < ids.length && rows.size() < limit; i++) rows.add(describe(s.getObject(ids[i])));
    return page(rows, ids.length, offset, limit);
  }
  private static Object page(List<?> rows, int total, int offset, int limit) {
    return Map.of("rows", rows, "total", total, "offset", offset, "limit", limit);
  }
  private static Object queryResult(ISnapshot s, Object result, int offset, int limit) throws Exception {
    if (result == null) return Collections.emptyList();
    if (result instanceof int[]) return objects(s, (int[]) result, offset, limit);
    if (result instanceof IStructuredResult) {
      var structured = (IStructuredResult) result;
      List<?> source;
      if (result instanceof IResultTable) {
        var table = (IResultTable) result;
        var rows = new ArrayList<Object>();
        for (int i = offset; i < table.getRowCount() && rows.size() < limit; i++) rows.add(tableRow(structured, table.getRow(i)));
        return page(rows, table.getRowCount(), offset, limit);
      }
      if (result instanceof IResultTree) {
        source = ((IResultTree) result).getElements();
        var rows = new ArrayList<Object>();
        for (int i = offset; i < source.size() && rows.size() < limit; i++) rows.add(tableRow(structured, source.get(i)));
        return page(rows, source.size(), offset, limit);
      }
    }
    if (result instanceof List<?>) {
      var list = (List<?>) result;
      var rows = new ArrayList<Object>();
      for (int i = offset; i < list.size() && rows.size() < limit; i++) rows.add(cell(list.get(i)));
      return page(rows, list.size(), offset, limit);
    }
    return Map.of("text", String.valueOf(result));
  }
  private static Object tableRow(IStructuredResult result, Object row) {
    var values = new LinkedHashMap<String,Object>();
    Column[] columns = result.getColumns();
    for (int i = 0; i < columns.length; i++) values.put(columns[i].getLabel(), cell(result.getColumnValue(row, i)));
    IContextObject context = result.getContext(row);
    if (context != null) values.put("objectId", context.getObjectId());
    return values;
  }
  private static Object cell(Object value) {
    if (value == null || value instanceof Number || value instanceof Boolean) return value;
    if (value instanceof IObject) return describe((IObject) value);
    return String.valueOf(value);
  }
  static String json(Object value) {
    if (value == null) return "null";
    if (value instanceof Double && !Double.isFinite((Double) value)) return "null";
    if (value instanceof Float && !Float.isFinite((Float) value)) return "null";
    if (value instanceof Number || value instanceof Boolean) return value.toString();
    if (value instanceof Map<?,?>) {
      var entries = new ArrayList<String>();
      ((Map<?,?>) value).forEach((k,v) -> entries.add(json(k.toString()) + ":" + json(v)));
      return "{" + String.join(",", entries) + "}";
    }
    if (value instanceof Iterable<?>) {
      var entries = new ArrayList<String>();
      for (Object item : (Iterable<?>) value) entries.add(json(item));
      return "[" + String.join(",", entries) + "]";
    }
    StringBuilder b = new StringBuilder("\"");
    for (char c : value.toString().toCharArray()) {
      switch(c) {
        case '"': b.append("\\\""); break;
        case '\\': b.append("\\\\"); break;
        default: if (c < 32 || Character.isSurrogate(c)) b.append(String.format("\\u%04x", (int)c)); else b.append(c);
      }
    }
    return b.append('"').toString();
  }
  @Override public void stop() { }
}
