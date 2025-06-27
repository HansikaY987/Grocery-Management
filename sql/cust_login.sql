

CREATE OR REPLACE PROCEDURE customer_login_log(p_user_id INT, p_details TEXT)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO log (user_id, action, details, created_at)
    VALUES (p_user_id, 'customer_login', p_details, NOW());
END;
$$;
