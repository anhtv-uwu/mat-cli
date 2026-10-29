package com.appiansupport.mat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.Base64;

/** Preserve native Windows Unicode arguments without depending on its ANSI code page. */
final class ArgumentTransport {
  static final String PROPERTY = "mat.cli.arguments";

  private static String[] payload() {
    String encoded = System.getProperty(PROPERTY);
    if (encoded == null) return null;
    String decoded = new String(Base64.getDecoder().decode(encoded), StandardCharsets.UTF_8);
    String[] values = decoded.split("\u0000", -1);
    if (values.length == 0 || !Path.of(values[0]).isAbsolute()) {
      throw new IllegalArgumentException("Invalid launcher working directory");
    }
    return values;
  }

  static String[] decode(String[] original) {
    String[] values = payload();
    return values == null ? original : Arrays.copyOfRange(values, 1, values.length);
  }

  static java.io.File heapFile(String value) {
    String[] values = payload();
    Path path = Path.of(value);
    if (values != null && !path.isAbsolute()) path = Path.of(values[0]).resolve(path);
    return path.toFile();
  }
}
