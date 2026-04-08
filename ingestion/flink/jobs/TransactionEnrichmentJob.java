import java.time.Instant;
import java.util.Properties;
import java.util.UUID;

import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.contrib.streaming.state.EmbeddedRocksDBStateBackend;
import org.apache.flink.runtime.state.hashmap.HashMapStateBackend;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaProducer;

public class TransactionEnrichmentJob {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        int parallelism = envIntOrDefault("ENRICH_PARALLELISM", 12);
        long minPauseBetweenCheckpointsMs = envLongOrDefault("MIN_PAUSE_BETWEEN_CHECKPOINTS_MS", 5000L);
        boolean enableUnalignedCheckpoints = envBoolOrDefault("ENABLE_UNALIGNED_CHECKPOINTS", true);
        String stateBackend = envOrDefault("ENRICH_STATE_BACKEND", "HASHMAP");

        env.setParallelism(parallelism);
        env.enableCheckpointing(30000);
        if (minPauseBetweenCheckpointsMs > 0) {
            env.getCheckpointConfig().setMinPauseBetweenCheckpoints(minPauseBetweenCheckpointsMs);
        }
        if (enableUnalignedCheckpoints) {
            env.getCheckpointConfig().enableUnalignedCheckpoints();
        }

        if ("ROCKSDB".equalsIgnoreCase(stateBackend)) {
            env.setStateBackend(new EmbeddedRocksDBStateBackend());
        } else {
            env.setStateBackend(new HashMapStateBackend());
        }

        Properties kafkaProps = buildKafkaProperties();

        // Source: raw-transactions Kafka topic
        FlinkKafkaConsumer<String> source = new FlinkKafkaConsumer<>(
            "raw-transactions",
            new SimpleStringSchema(),
            kafkaProps
        );
        source.setStartFromLatest();
        DataStream<String> rawTxnStream = env.addSource(source).name("raw-transactions-source");

        // Minimal enrichment stage for pipeline validation. This keeps event payload intact
        // while attaching deterministic metadata needed by downstream services.
        DataStream<String> enriched = rawTxnStream
            .map(TransactionEnrichmentJob::enrichEvent)
            .name("transaction-enrichment");

        // Sink: enriched-transactions Kafka topic
        enriched.addSink(new FlinkKafkaProducer<>(
            "enriched-transactions",
            new SimpleStringSchema(),
            kafkaProps
        )).name("enriched-transactions-sink");

        env.execute("TransactionEnrichmentJob");
    }

    private static Properties buildKafkaProperties() {
        Properties props = new Properties();
        props.setProperty("bootstrap.servers", envOrDefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"));
        props.setProperty("group.id", envOrDefault("KAFKA_GROUP_ID", "unigraph-transaction-enrichment"));
        props.setProperty("auto.offset.reset", envOrDefault("KAFKA_AUTO_OFFSET_RESET", "latest"));
        props.setProperty("linger.ms", envOrDefault("KAFKA_PRODUCER_LINGER_MS", "2"));
        props.setProperty("compression.type", envOrDefault("KAFKA_PRODUCER_COMPRESSION_TYPE", "lz4"));
        return props;
    }

    private static String enrichEvent(String rawEvent) {
        String payload = rawEvent == null ? "" : rawEvent.trim();
        String safePayload = payload.startsWith("{") ? payload : quoteAsJsonString(payload);
        String enrichmentMeta = String.format(
            "\"ingest_ts\":\"%s\",\"pipeline_version\":\"v1\",\"event_uid\":\"%s\"",
            Instant.now().toString(),
            UUID.randomUUID().toString()
        );
        return String.format("{\"raw_event\":%s,\"enrichment\":{%s}}", safePayload, enrichmentMeta);
    }

    private static String quoteAsJsonString(String value) {
        String escaped = value
            .replace("\\", "\\\\")
            .replace("\"", "\\\"");
        return "\"" + escaped + "\"";
    }

    private static String envOrDefault(String key, String defaultValue) {
        String value = System.getenv(key);
        if (value == null || value.trim().isEmpty()) {
            return defaultValue;
        }
        return value;
    }

    private static int envIntOrDefault(String key, int defaultValue) {
        String raw = System.getenv(key);
        if (raw == null || raw.trim().isEmpty()) {
            return defaultValue;
        }
        try {
            return Integer.parseInt(raw.trim());
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
    }

    private static long envLongOrDefault(String key, long defaultValue) {
        String raw = System.getenv(key);
        if (raw == null || raw.trim().isEmpty()) {
            return defaultValue;
        }
        try {
            return Long.parseLong(raw.trim());
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
    }

    private static boolean envBoolOrDefault(String key, boolean defaultValue) {
        String raw = System.getenv(key);
        if (raw == null || raw.trim().isEmpty()) {
            return defaultValue;
        }
        return Boolean.parseBoolean(raw.trim());
    }
}
