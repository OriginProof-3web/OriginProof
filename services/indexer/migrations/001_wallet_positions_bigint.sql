-- AI(Codex), requested by B: preserve existing journal/checkpoint rows and keys.
-- PostgreSQL only. Stop indexer writers and back up the target DB before applying.
BEGIN;
SET LOCAL lock_timeout = '5s';
LOCK TABLE wallet_events, wallet_checkpoints IN ACCESS EXCLUSIVE MODE;
ALTER TABLE wallet_events
    ALTER COLUMN block_number TYPE BIGINT USING block_number::BIGINT,
    ALTER COLUMN log_index TYPE BIGINT USING log_index::BIGINT;
ALTER TABLE wallet_checkpoints
    ALTER COLUMN block_number TYPE BIGINT USING block_number::BIGINT;
COMMIT;
