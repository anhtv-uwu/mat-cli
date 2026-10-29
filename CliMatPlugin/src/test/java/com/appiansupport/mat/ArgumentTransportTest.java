package com.appiansupport.mat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Base64;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ArgumentTransportTest {
  @AfterEach void clearTransport() { System.clearProperty(ArgumentTransport.PROPERTY); }

  private void encode(String... values) {
    System.setProperty(ArgumentTransport.PROPERTY, Base64.getEncoder().encodeToString(
        String.join("\u0000", values).getBytes(StandardCharsets.UTF_8)));
  }

  @Test void noTransportKeepsNormalArguments() {
    String[] args = {"info", "heap.hprof"};
    assertSame(args, ArgumentTransport.decode(args));
  }

  @Test void preservesUnicodeQuotesBackslashesAndEmptyArgument() {
    String cwd = Path.of(".").toAbsolutePath().normalize().toString();
    String[] args = {"oql", "tiếng Việt.hprof", "SELECT \"quoted value\"", "", "a\\b\\"};
    encode(cwd, args[0], args[1], args[2], args[3], args[4]);
    assertArrayEquals(args, ArgumentTransport.decode(new String[0]));
    assertEquals(Path.of(cwd).resolve(args[1]), ArgumentTransport.heapFile(args[1]).toPath());
  }

  @Test void directoryWithoutArgumentsDecodesToEmptyArray() {
    encode(Path.of(".").toAbsolutePath().toString());
    assertEquals(0, ArgumentTransport.decode(new String[0]).length);
  }

  @Test void rejectsRelativeWorkingDirectory() {
    encode("relative-directory", "info");
    assertThrows(IllegalArgumentException.class, () -> ArgumentTransport.decode(new String[0]));
  }

  @Test void jsonRemainsAsciiWithoutLosingUnicode() {
    String result = AgentApplication.json(Map.of("name", "tiếng Việt 😀"));
    assertTrue(result.chars().allMatch(c -> c >= 32 && c <= 126));
    assertTrue(result.contains("\\u1ebf"));
    assertTrue(result.contains("\\ud83d\\ude00"));
  }
}
