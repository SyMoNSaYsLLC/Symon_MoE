package com.symoneural;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * GGUFMetaReader — reads metadata KV pairs from a GGUF binary file.
 *
 * <p>Supports GGUF versions 1, 2, and 3.  Tensor data is not loaded into
 * memory; only the tensor info table (name, shape, type, data offset) is
 * parsed alongside the metadata.
 *
 * <p>Usage:
 * <pre>{@code
 *   GGUFMetaReader reader = new GGUFMetaReader("path/to/model.gguf");
 *   Map<String, Object> meta = reader.getMetadata();
 *   List<TensorInfo> tensors = reader.getTensors();
 * }</pre>
 */
public class GGUFMetaReader {

    private static final int  GGUF_MAGIC   = 0x46554747; // "GGUF" LE
    private static final byte VALUE_UINT8  = 0;
    private static final byte VALUE_INT8   = 1;
    private static final byte VALUE_UINT16 = 2;
    private static final byte VALUE_INT16  = 3;
    private static final byte VALUE_UINT32 = 4;
    private static final byte VALUE_INT32  = 5;
    private static final byte VALUE_FLOAT  = 6;
    private static final byte VALUE_BOOL   = 7;
    private static final byte VALUE_STRING = 8;
    private static final byte VALUE_ARRAY  = 9;
    private static final byte VALUE_UINT64 = 10;
    private static final byte VALUE_INT64  = 11;
    private static final byte VALUE_DOUBLE = 12;

    // ------------------------------------------------------------------ //
    // Inner types
    // ------------------------------------------------------------------ //

    /** Tensor descriptor — metadata only, no tensor data. */
    public static class TensorInfo {
        public final String   name;
        public final long[]   shape;
        public final long     ggmlType;
        public final long     dataOffset;

        TensorInfo(String name, long[] shape, long ggmlType, long dataOffset) {
            this.name       = name;
            this.shape      = shape;
            this.ggmlType   = ggmlType;
            this.dataOffset = dataOffset;
        }

        @Override
        public String toString() {
            return String.format("TensorInfo{name='%s', shape=%s, type=%d, offset=%d}",
                    name, Arrays.toString(shape), ggmlType, dataOffset);
        }
    }

    // ------------------------------------------------------------------ //
    // Fields
    // ------------------------------------------------------------------ //

    private final Map<String, Object> metadata = new LinkedHashMap<>();
    private final List<TensorInfo>    tensors  = new ArrayList<>();
    private int version;

    // ------------------------------------------------------------------ //
    // Constructor
    // ------------------------------------------------------------------ //

    public GGUFMetaReader(String path) throws IOException {
        parse(Path.of(path));
    }

    public GGUFMetaReader(Path path) throws IOException {
        parse(path);
    }

    // ------------------------------------------------------------------ //
    // Public accessors
    // ------------------------------------------------------------------ //

    public int                getVersion()  { return version; }
    public Map<String, Object> getMetadata() { return Collections.unmodifiableMap(metadata); }
    public List<TensorInfo>   getTensors()  { return Collections.unmodifiableList(tensors); }

    public String getString(String key, String fallback) {
        Object v = metadata.get(key);
        return (v instanceof String) ? (String) v : fallback;
    }

    public long getLong(String key, long fallback) {
        Object v = metadata.get(key);
        if (v instanceof Number) return ((Number) v).longValue();
        return fallback;
    }

    // ------------------------------------------------------------------ //
    // Parsing
    // ------------------------------------------------------------------ //

    private void parse(Path path) throws IOException {
        byte[] bytes = Files.readAllBytes(path);
        ByteBuffer buf = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);

        int magic = buf.getInt();
        if (magic != GGUF_MAGIC)
            throw new IOException("Not a GGUF file (bad magic): " + path);

        version = buf.getInt();
        if (version < 1 || version > 3)
            throw new IOException("Unsupported GGUF version: " + version);

        long tensorCount = (version == 1) ? Integer.toUnsignedLong(buf.getInt()) : buf.getLong();
        long kvCount     = (version == 1) ? Integer.toUnsignedLong(buf.getInt()) : buf.getLong();

        // Metadata
        for (long i = 0; i < kvCount; i++) {
            String key   = readString(buf);
            int    vtype = buf.getInt();
            Object value = readValue(buf, vtype);
            metadata.put(key, value);
        }

        // Tensor info
        for (long i = 0; i < tensorCount; i++) {
            String name   = readString(buf);
            int    nDims  = buf.getInt();
            long[] shape  = new long[nDims];
            for (int d = 0; d < nDims; d++) shape[d] = buf.getLong();
            long type   = Integer.toUnsignedLong(buf.getInt());
            long offset = buf.getLong();
            tensors.add(new TensorInfo(name, shape, type, offset));
        }
    }

    private String readString(ByteBuffer buf) {
        long len = buf.getLong();
        byte[] bytes = new byte[(int) len];
        buf.get(bytes);
        return new String(bytes, StandardCharsets.UTF_8);
    }

    @SuppressWarnings("unchecked")
    private Object readValue(ByteBuffer buf, int vtype) throws IOException {
        return switch (vtype) {
            case VALUE_UINT8  -> Byte.toUnsignedInt(buf.get());
            case VALUE_INT8   -> (int) buf.get();
            case VALUE_UINT16 -> Short.toUnsignedInt(buf.getShort());
            case VALUE_INT16  -> (int) buf.getShort();
            case VALUE_UINT32 -> Integer.toUnsignedLong(buf.getInt());
            case VALUE_INT32  -> buf.getInt();
            case VALUE_FLOAT  -> buf.getFloat();
            case VALUE_BOOL   -> buf.get() != 0;
            case VALUE_STRING -> readString(buf);
            case VALUE_UINT64 -> buf.getLong();
            case VALUE_INT64  -> buf.getLong();
            case VALUE_DOUBLE -> buf.getDouble();
            case VALUE_ARRAY  -> {
                int  elemType = buf.getInt();
                long count    = buf.getLong();
                List<Object> items = new ArrayList<>((int) Math.min(count, 4096));
                for (long j = 0; j < count; j++) items.add(readValue(buf, elemType));
                yield items;
            }
            default -> throw new IOException("Unknown GGUF value type: " + vtype);
        };
    }

    // ------------------------------------------------------------------ //
    // CLI entry point
    // ------------------------------------------------------------------ //

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: GGUFMetaReader <path.gguf> [--tensors]");
            System.exit(1);
        }
        boolean showTensors = args.length > 1 && "--tensors".equals(args[1]);
        GGUFMetaReader reader = new GGUFMetaReader(args[0]);
        if (showTensors) {
            for (TensorInfo t : reader.getTensors()) System.out.println(t);
        } else {
            for (Map.Entry<String, Object> e : reader.getMetadata().entrySet())
                System.out.printf("%-40s = %s%n", e.getKey(), e.getValue());
        }
    }
}
