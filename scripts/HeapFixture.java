import com.sun.management.HotSpotDiagnosticMXBean;
import java.lang.management.ManagementFactory;
import java.util.ArrayList;
import java.util.List;

/** Synthetic data only; no user heap is needed for validation. */
public final class HeapFixture {
    static final List<Object> ROOT = new ArrayList<>();
    public static void main(String[] args) throws Exception {
        for (int i = 0; i < 128; i++) {
            ROOT.add("mat-cli-fixture-" + i);
            ROOT.add(new byte[4096]);
        }
        ManagementFactory.getPlatformMXBean(HotSpotDiagnosticMXBean.class)
            .dumpHeap(args[0], true);
        System.out.println(ROOT.size());
    }
}
