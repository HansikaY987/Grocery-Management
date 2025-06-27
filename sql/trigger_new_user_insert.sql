-- Step 1: Create the trigger function
CREATE OR REPLACE FUNCTION log_user_registration()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO log (user_id, action, details, created_at)
    VALUES (NEW.id, 'registration', 'New user ' || NEW.username || ' registered', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 2: Create the trigger
CREATE TRIGGER after_user_insert
AFTER INSERT ON "user"
FOR EACH ROW
EXECUTE FUNCTION log_user_registration();