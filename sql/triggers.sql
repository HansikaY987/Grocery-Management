-- Create order log table
CREATE TABLE IF NOT EXISTS order_log (
    id SERIAL PRIMARY KEY,
    order_id INT,
    user_id INT,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger function to log orders
CREATE OR REPLACE FUNCTION log_order()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO order_log (order_id, user_id)
    VALUES (NEW.id, NEW.user_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger after order insert
DROP TRIGGER IF EXISTS after_order_insert ON "order";
CREATE TRIGGER after_order_insert
AFTER INSERT ON "order"
FOR EACH ROW
EXECUTE FUNCTION log_order();
