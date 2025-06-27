CREATE OR REPLACE PROCEDURE update_or_remove_cart_item(p_item_id INT, p_quantity INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_id INT;
    v_old_quantity INT;
BEGIN
    -- Get user ID and current quantity using cart item ID
    SELECT user_id, quantity
    INTO v_user_id, v_old_quantity
    FROM cart_item
    WHERE id = p_item_id;

    IF NOT FOUND THEN
        RAISE NOTICE 'No cart item found with id %', p_item_id;
        RETURN;
    END IF;

    IF p_quantity <= 0 THEN
        -- Remove item
        DELETE FROM cart_item WHERE id = p_item_id;

        -- Log deletion
        INSERT INTO log(user_id, action, details, created_at)
        VALUES (
            v_user_id,
            'remove_cart_item',
            'Removed cart item ID ' || p_item_id,
            NOW()
        );
    ELSE
        -- Update quantity
        UPDATE cart_item
        SET quantity = p_quantity
        WHERE id = p_item_id;

        -- Log update
        INSERT INTO log(user_id, action, details, created_at)
        VALUES (
            v_user_id,
            'update_cart_item',
            'Updated cart item ID ' || p_item_id || ' from ' || v_old_quantity || ' to ' || p_quantity,
            NOW()
        );
    END IF;
END;
$$;
