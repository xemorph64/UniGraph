import java.time.Instant;
import java.util.Properties;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.api.java.functions.KeySelector;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.datastream.KeyedStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.assigners.SlidingProcessingTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer;
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaProducer;
import org.apache.flink.util.Collector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AnomalyWindowJob {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final Logger LOG = LoggerFactory.getLogger(AnomalyWindowJob.class);

    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        int parallelism = envIntOrDefault("ANOMALY_PARALLELISM", 12);
        long minPauseBetweenCheckpointsMs = envLongOrDefault("MIN_PAUSE_BETWEEN_CHECKPOINTS_MS", 5000L);
        boolean enableUnalignedCheckpoints = envBoolOrDefault("ENABLE_UNALIGNED_CHECKPOINTS", true);

        env.setParallelism(parallelism);
        env.enableCheckpointing(30000);
        if (minPauseBetweenCheckpointsMs > 0) {
            env.getCheckpointConfig().setMinPauseBetweenCheckpoints(minPauseBetweenCheckpointsMs);
        }
        if (enableUnalignedCheckpoints) {
            env.getCheckpointConfig().enableUnalignedCheckpoints();
        }

        Properties kafkaProps = buildKafkaProperties();

        FlinkKafkaConsumer<String> source = new FlinkKafkaConsumer<>(
            "enriched-transactions",
            new SimpleStringSchema(),
            kafkaProps
        );
        source.setStartFromLatest();

        boolean fastE2EWindows = Boolean.parseBoolean(envOrDefault("ANOMALY_FAST_E2E", "true"));
        Time fiveMinuteSize = fastE2EWindows ? Time.seconds(10) : Time.minutes(5);
        Time fiveMinuteSlide = fastE2EWindows ? Time.seconds(2) : Time.minutes(1);
        Time oneHourSize = fastE2EWindows ? Time.seconds(30) : Time.hours(1);
        Time oneHourSlide = fastE2EWindows ? Time.seconds(5) : Time.minutes(5);
        Time twentyFourHourSize = fastE2EWindows ? Time.minutes(2) : Time.hours(24);
        Time twentyFourHourSlide = fastE2EWindows ? Time.seconds(10) : Time.hours(1);

        DataStream<TransactionRecord> events = env
            .addSource(source)
            .name("enriched-transactions-source")
            .map(AnomalyWindowJob::parseRecord)
            .filter(record -> record != null)
            .name("parse-transaction-record");

        KeyedStream<TransactionRecord, String> keyedByAccount = events
            .keyBy((KeySelector<TransactionRecord, String>) record -> record.accountId);

        DataStream<String> immediateHighValue = events
            .map(AnomalyWindowJob::buildImmediateHighValueViolation)
            .filter(line -> line != null)
            .name("immediate-high-value-violations");

        DataStream<String> fiveMinuteVelocity = buildVelocityStream(
            keyedByAccount,
            fastE2EWindows ? "10s" : "5m",
            fiveMinuteSize,
            fiveMinuteSlide,
            12,
            300000.0
        );

        DataStream<String> oneHourVelocity = buildVelocityStream(
            keyedByAccount,
            fastE2EWindows ? "30s" : "1h",
            oneHourSize,
            oneHourSlide,
            30,
            1200000.0
        );

        DataStream<String> twentyFourHourVelocity = buildVelocityStream(
            keyedByAccount,
            fastE2EWindows ? "2m" : "24h",
            twentyFourHourSize,
            twentyFourHourSlide,
            80,
            5000000.0
        );

        DataStream<String> violations = fiveMinuteVelocity
            .union(oneHourVelocity)
            .union(twentyFourHourVelocity)
            .union(immediateHighValue);

        violations.addSink(new FlinkKafkaProducer<>(
            "rule-violations",
            new SimpleStringSchema(),
            kafkaProps
        )).name("rule-violations-sink");

        env.execute("AnomalyWindowJob");
    }

    private static DataStream<String> buildVelocityStream(
        KeyedStream<TransactionRecord, String> keyedByAccount,
        String windowLabel,
        Time size,
        Time slide,
        long countThreshold,
        double amountThreshold
    ) {
        return keyedByAccount
            .window(SlidingProcessingTimeWindows.of(size, slide))
            .aggregate(
                new VelocityAggregate(),
                new VelocityWindowFunction(windowLabel, countThreshold, amountThreshold)
            )
            .filter(line -> line != null)
            .name("velocity-window-" + windowLabel);
    }

    private static Properties buildKafkaProperties() {
        Properties props = new Properties();
        props.setProperty("bootstrap.servers", envOrDefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"));
        props.setProperty("group.id", envOrDefault("KAFKA_GROUP_ID", "unigraph-anomaly-window"));
        props.setProperty("auto.offset.reset", envOrDefault("KAFKA_AUTO_OFFSET_RESET", "latest"));
        props.setProperty("linger.ms", envOrDefault("KAFKA_PRODUCER_LINGER_MS", "2"));
        props.setProperty("compression.type", envOrDefault("KAFKA_PRODUCER_COMPRESSION_TYPE", "lz4"));
        return props;
    }

    private static TransactionRecord parseRecord(String payload) {
        if (payload == null || payload.trim().isEmpty()) {
            return null;
        }

        try {
            JsonNode root = OBJECT_MAPPER.readTree(payload);
            JsonNode eventNode = extractEventNode(root);
            if (eventNode == null || eventNode.isMissingNode()) {
                return null;
            }

            String accountId = textOrEmpty(eventNode, "from_account");
            if (accountId.isEmpty()) {
                accountId = textOrEmpty(eventNode, "account_id");
            }
            if (accountId.isEmpty()) {
                return null;
            }

            double amount = asDoubleOrDefault(eventNode, "amount", Double.NaN);
            if (!Double.isFinite(amount)) {
                amount = asDoubleOrDefault(eventNode, "txn_amount", Double.NaN);
            }
            if (!Double.isFinite(amount)) {
                return null;
            }

            String timestampText = textOrEmpty(eventNode, "timestamp");
            if (timestampText.isEmpty()) {
                timestampText = textOrEmpty(eventNode, "event_ts");
            }

            String txnId = textOrEmpty(eventNode, "txn_id");
            long eventTimeMs = parseTimestamp(timestampText);

            return new TransactionRecord(accountId, amount, eventTimeMs, txnId);
        } catch (Exception ex) {
            // Keep the job healthy while making parse drops visible in logs.
            LOG.warn("Dropping enriched record due to parse error. payload={}", abbreviate(payload), ex);
            return null;
        }
    }

    private static JsonNode extractEventNode(JsonNode root) throws Exception {
        JsonNode candidate = root;

        if (root.has("raw_event")) {
            JsonNode rawEventNode = root.path("raw_event");
            if (rawEventNode.isTextual()) {
                String rawText = rawEventNode.asText("");
                if (rawText.isEmpty()) {
                    return null;
                }
                rawEventNode = OBJECT_MAPPER.readTree(rawText);
            }
            candidate = rawEventNode;
        }

        if (candidate.has("payload")) {
            candidate = candidate.path("payload");
        }
        if (candidate.has("after")) {
            candidate = candidate.path("after");
        }

        return candidate;
    }

    private static String textOrEmpty(JsonNode node, String field) {
        if (node == null || field == null || !node.has(field)) {
            return "";
        }
        return node.path(field).asText("").trim();
    }

    private static double asDoubleOrDefault(JsonNode node, String field, double fallback) {
        if (node == null || field == null || !node.has(field)) {
            return fallback;
        }
        JsonNode valueNode = node.path(field);
        if (valueNode.isNumber()) {
            return valueNode.asDouble();
        }
        if (valueNode.isTextual()) {
            try {
                return Double.parseDouble(valueNode.asText().trim());
            } catch (NumberFormatException ignored) {
                return fallback;
            }
        }
        return fallback;
    }

    private static String abbreviate(String value) {
        if (value == null) {
            return "null";
        }
        String normalized = value.replace("\r", " ").replace("\n", " ").trim();
        if (normalized.length() <= 280) {
            return normalized;
        }
        return normalized.substring(0, 280) + "...";
    }

    private static long parseTimestamp(String timestamp) {
        try {
            if (timestamp != null && !timestamp.isEmpty()) {
                return Instant.parse(timestamp).toEpochMilli();
            }
        } catch (Exception ignored) {
            // Fall back to processing time when upstream timestamps are malformed.
        }
        return System.currentTimeMillis();
    }

    private static String buildImmediateHighValueViolation(TransactionRecord record) {
        if (record.amount < 300000.0) {
            return null;
        }

        return String.format(
            "{\"rule\":\"high_value_immediate\",\"window\":\"instant\",\"account_id\":\"%s\",\"txn_id\":\"%s\",\"txn_count\":1,\"total_amount\":%.2f,\"count_threshold\":1,\"amount_threshold\":300000.00,\"window_end\":\"%s\",\"is_flagged\":true}",
            record.accountId,
            record.txnId,
            record.amount,
            Instant.now().toString()
        );
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

    private static final class TransactionRecord {
        private final String accountId;
        private final double amount;
        private final long eventTimeMs;
        private final String txnId;

        private TransactionRecord(String accountId, double amount, long eventTimeMs, String txnId) {
            this.accountId = accountId;
            this.amount = amount;
            this.eventTimeMs = eventTimeMs;
            this.txnId = txnId == null ? "" : txnId;
        }
    }

    private static final class VelocityAccumulator {
        private long count;
        private double totalAmount;
    }

    private static final class VelocitySummary {
        private final long count;
        private final double totalAmount;

        private VelocitySummary(long count, double totalAmount) {
            this.count = count;
            this.totalAmount = totalAmount;
        }
    }

    private static final class VelocityAggregate implements AggregateFunction<TransactionRecord, VelocityAccumulator, VelocitySummary> {
        @Override
        public VelocityAccumulator createAccumulator() {
            return new VelocityAccumulator();
        }

        @Override
        public VelocityAccumulator add(TransactionRecord value, VelocityAccumulator accumulator) {
            accumulator.count += 1;
            accumulator.totalAmount += value.amount;
            return accumulator;
        }

        @Override
        public VelocitySummary getResult(VelocityAccumulator accumulator) {
            return new VelocitySummary(accumulator.count, accumulator.totalAmount);
        }

        @Override
        public VelocityAccumulator merge(VelocityAccumulator a, VelocityAccumulator b) {
            a.count += b.count;
            a.totalAmount += b.totalAmount;
            return a;
        }
    }

    private static final class VelocityWindowFunction extends ProcessWindowFunction<VelocitySummary, String, String, TimeWindow> {
        private final String windowLabel;
        private final long countThreshold;
        private final double amountThreshold;

        private VelocityWindowFunction(String windowLabel, long countThreshold, double amountThreshold) {
            this.windowLabel = windowLabel;
            this.countThreshold = countThreshold;
            this.amountThreshold = amountThreshold;
        }

        @Override
        public void process(String key, Context context, Iterable<VelocitySummary> summaries, Collector<String> out) {
            VelocitySummary summary = summaries.iterator().next();
            boolean flagged = summary.count >= countThreshold || summary.totalAmount >= amountThreshold;
            if (!flagged) {
                return;
            }

            String event = String.format(
                "{\"rule\":\"velocity\",\"window\":\"%s\",\"account_id\":\"%s\",\"txn_count\":%d,\"total_amount\":%.2f,\"count_threshold\":%d,\"amount_threshold\":%.2f,\"window_end\":\"%s\",\"is_flagged\":true}",
                windowLabel,
                key,
                summary.count,
                summary.totalAmount,
                countThreshold,
                amountThreshold,
                Instant.ofEpochMilli(context.window().getEnd()).toString()
            );
            out.collect(event);
        }
    }
}
