CREATE TABLE strategy_signals (
    id UUID PRIMARY KEY,
    coin TEXT NOT NULL,
    model_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    signal JSONB  -- contains action, entry, stop_loss, take_profit
);