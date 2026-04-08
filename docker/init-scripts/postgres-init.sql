CREATE TABLE IF NOT EXISTS public.transactions (
    txn_id VARCHAR(64) PRIMARY KEY,
    from_account VARCHAR(32) NOT NULL,
    to_account VARCHAR(32) NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    channel VARCHAR(16) NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    customer_id VARCHAR(32) NOT NULL,
    device_fingerprint VARCHAR(128) NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    location JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON public.transactions ("timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_channel ON public.transactions (channel);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_publication
        WHERE pubname = 'unigraph_pub'
    ) THEN
        CREATE PUBLICATION unigraph_pub FOR TABLE public.transactions;
    END IF;
END
$$;

INSERT INTO public.transactions (
    txn_id,
    from_account,
    to_account,
    amount,
    channel,
    "timestamp",
    customer_id,
    device_fingerprint,
    ip_address,
    location
) VALUES
('TXN-NORM-00001', 'UBI30100010000001', 'UBI30100020000001', 2895.50, 'UPI',  '2026-04-07T10:00:00Z', 'CUST-UBI-1000001', 'sha256:dev-00000a01', 'sha256:ip-00000a01', '{"lat": 19.0760, "lon": 72.8777}'),
('TXN-NORM-00002', 'UBI30100010000002', 'UBI30100020000002', 15420.00, 'IMPS', '2026-04-07T10:03:00Z', 'CUST-UBI-1000002', 'sha256:dev-00000a02', 'sha256:ip-00000a02', '{"lat": 18.5204, "lon": 73.8567}'),
('TXN-NORM-00003', 'UBI30100010000003', 'UBI30100020000003', 48250.75, 'NEFT', '2026-04-07T10:08:00Z', 'CUST-UBI-1000003', 'sha256:dev-00000a03', 'sha256:ip-00000a03', '{"lat": 12.9716, "lon": 77.5946}'),
('TXN-NORM-00004', 'UBI30100010000004', 'UBI30100020000004', 8600.00,  'UPI',  '2026-04-07T10:13:00Z', 'CUST-UBI-1000004', 'sha256:dev-00000a04', 'sha256:ip-00000a04', '{"lat": 28.6139, "lon": 77.2090}'),
('TXN-NORM-00005', 'UBI30100010000005', 'UBI30100020000005', 320000.00,'RTGS', '2026-04-07T10:18:00Z', 'CUST-UBI-1000005', 'sha256:dev-00000a05', 'sha256:ip-00000a05', '{"lat": 13.0827, "lon": 80.2707}'),
('TXN-HVRP-00006', 'UBI30100090000001', 'UBI30100090010001', 990500.00,'NEFT', '2026-04-07T10:20:00Z', 'CUST-UBI-9000001', 'sha256:dev-00aml001', 'sha256:ip-00aml001', '{"lat": 22.5726, "lon": 88.3639}'),
('TXN-HVRP-00007', 'UBI30100090000001', 'UBI30100090010002', 993200.00,'IMPS', '2026-04-07T10:22:00Z', 'CUST-UBI-9000001', 'sha256:dev-00aml001', 'sha256:ip-00aml001', '{"lat": 22.5726, "lon": 88.3639}'),
('TXN-HVRP-00008', 'UBI30100090000001', 'UBI30100090010003', 996900.00,'RTGS', '2026-04-07T10:24:00Z', 'CUST-UBI-9000001', 'sha256:dev-00aml001', 'sha256:ip-00aml001', '{"lat": 22.5726, "lon": 88.3639}'),
('TXN-HVRP-00009', 'UBI30100090000001', 'UBI30100090010004', 985750.00,'NEFT', '2026-04-07T10:26:00Z', 'CUST-UBI-9000001', 'sha256:dev-00aml001', 'sha256:ip-00aml001', '{"lat": 22.5726, "lon": 88.3639}'),
('TXN-HVRP-00010', 'UBI30100090000001', 'UBI30100090010005', 992100.00,'IMPS', '2026-04-07T10:28:00Z', 'CUST-UBI-9000001', 'sha256:dev-00aml001', 'sha256:ip-00aml001', '{"lat": 22.5726, "lon": 88.3639}');
