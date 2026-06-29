package com.symoneural;

import com.google.gson.*;
import okhttp3.*;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * OllamaClient — Java HTTP client for the Ollama REST API.
 *
 * <p>Uses OkHttp for synchronous and streaming requests.
 *
 * <p>Usage:
 * <pre>{@code
 *   OllamaClient client = new OllamaClient("http://localhost:11434");
 *   String response = client.generate("llama3", "Hello!");
 *   System.out.println(response);
 * }</pre>
 */
public class OllamaClient {

    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");

    private final String     baseUrl;
    private final OkHttpClient http;
    private final Gson       gson;

    // ------------------------------------------------------------------ //
    // Constructor
    // ------------------------------------------------------------------ //

    public OllamaClient(String baseUrl) {
        this.baseUrl = baseUrl.replaceAll("/$", "");
        this.http = new OkHttpClient.Builder()
                .connectTimeout(30,  TimeUnit.SECONDS)
                .readTimeout(120,    TimeUnit.SECONDS)
                .writeTimeout(30,    TimeUnit.SECONDS)
                .build();
        this.gson = new GsonBuilder().setPrettyPrinting().create();
    }

    // ------------------------------------------------------------------ //
    // Inner types
    // ------------------------------------------------------------------ //

    public record ChatMessage(String role, String content) {}

    public record ModelInfo(String name, String modified_at, long size) {}

    // ------------------------------------------------------------------ //
    // API methods
    // ------------------------------------------------------------------ //

    /**
     * List all models available in the Ollama instance.
     */
    public List<ModelInfo> listModels() throws IOException {
        Request req = new Request.Builder()
                .url(baseUrl + "/api/tags")
                .get()
                .build();
        try (Response resp = http.newCall(req).execute()) {
            requireOk(resp);
            JsonObject obj = gson.fromJson(resp.body().charStream(), JsonObject.class);
            JsonArray models = obj.getAsJsonArray("models");
            List<ModelInfo> result = new ArrayList<>();
            for (JsonElement elem : models) {
                JsonObject m = elem.getAsJsonObject();
                result.add(new ModelInfo(
                        m.get("name").getAsString(),
                        m.has("modified_at") ? m.get("modified_at").getAsString() : null,
                        m.has("size") ? m.get("size").getAsLong() : 0L
                ));
            }
            return result;
        }
    }

    /**
     * Generate a completion (blocking, non-streaming).
     */
    public String generate(String model, String prompt) throws IOException {
        return generate(model, prompt, null);
    }

    /**
     * Generate a completion with optional additional options (blocking).
     *
     * @param options JSON object of Ollama generation parameters, or null.
     */
    public String generate(String model, String prompt, JsonObject options) throws IOException {
        JsonObject body = new JsonObject();
        body.addProperty("model",  model);
        body.addProperty("prompt", prompt);
        body.addProperty("stream", false);
        if (options != null) body.add("options", options);

        Request req = new Request.Builder()
                .url(baseUrl + "/api/generate")
                .post(RequestBody.create(gson.toJson(body), JSON))
                .build();
        try (Response resp = http.newCall(req).execute()) {
            requireOk(resp);
            JsonObject result = gson.fromJson(resp.body().charStream(), JsonObject.class);
            return result.get("response").getAsString();
        }
    }

    /**
     * Stream a generate response token-by-token.
     *
     * @param onToken callback invoked for each partial token string.
     */
    public void generateStream(String model, String prompt, java.util.function.Consumer<String> onToken)
            throws IOException {
        JsonObject body = new JsonObject();
        body.addProperty("model",  model);
        body.addProperty("prompt", prompt);
        body.addProperty("stream", true);

        Request req = new Request.Builder()
                .url(baseUrl + "/api/generate")
                .post(RequestBody.create(gson.toJson(body), JSON))
                .build();
        try (Response resp = http.newCall(req).execute()) {
            requireOk(resp);
            var source = resp.body().source();
            while (!source.exhausted()) {
                String line = source.readUtf8Line();
                if (line == null || line.isBlank()) continue;
                JsonObject chunk = gson.fromJson(line, JsonObject.class);
                onToken.accept(chunk.get("response").getAsString());
                if (chunk.has("done") && chunk.get("done").getAsBoolean()) break;
            }
        }
    }

    /**
     * Send a list of chat messages and return the assistant reply.
     */
    public ChatMessage chat(String model, List<ChatMessage> messages) throws IOException {
        JsonObject body = new JsonObject();
        body.addProperty("model",  model);
        body.addProperty("stream", false);
        body.add("messages", gson.toJsonTree(messages));

        Request req = new Request.Builder()
                .url(baseUrl + "/api/chat")
                .post(RequestBody.create(gson.toJson(body), JSON))
                .build();
        try (Response resp = http.newCall(req).execute()) {
            requireOk(resp);
            JsonObject result  = gson.fromJson(resp.body().charStream(), JsonObject.class);
            JsonObject message = result.getAsJsonObject("message");
            return new ChatMessage(
                    message.get("role").getAsString(),
                    message.get("content").getAsString()
            );
        }
    }

    /**
     * Get an embedding vector for a prompt.
     */
    public double[] embeddings(String model, String prompt) throws IOException {
        JsonObject body = new JsonObject();
        body.addProperty("model",  model);
        body.addProperty("prompt", prompt);

        Request req = new Request.Builder()
                .url(baseUrl + "/api/embeddings")
                .post(RequestBody.create(gson.toJson(body), JSON))
                .build();
        try (Response resp = http.newCall(req).execute()) {
            requireOk(resp);
            JsonObject result = gson.fromJson(resp.body().charStream(), JsonObject.class);
            JsonArray  arr    = result.getAsJsonArray("embedding");
            double[]   vec    = new double[arr.size()];
            for (int i = 0; i < arr.size(); i++) vec[i] = arr.get(i).getAsDouble();
            return vec;
        }
    }

    // ------------------------------------------------------------------ //
    // Helpers
    // ------------------------------------------------------------------ //

    private void requireOk(Response resp) throws IOException {
        if (!resp.isSuccessful())
            throw new IOException("Ollama API error " + resp.code() + ": " +
                    (resp.body() != null ? resp.body().string() : "(no body)"));
    }

    // ------------------------------------------------------------------ //
    // CLI
    // ------------------------------------------------------------------ //

    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.err.println("Usage: OllamaClient <base_url> <model> <prompt>");
            System.exit(1);
        }
        OllamaClient client = new OllamaClient(args[0]);
        String result = client.generate(args[1], args[2]);
        System.out.println(result);
    }
}
