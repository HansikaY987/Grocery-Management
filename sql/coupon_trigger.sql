CREATE OR REPLACE PROCEDURE apply_coupon_discount()
LANGUAGE plpgsql
AS $$
DECLARE
    v_coupon_id INT;
    v_discount_percentage NUMERIC;
    v_min_purchase NUMERIC;
    v_valid_from TIMESTAMP;
    v_valid_until TIMESTAMP;
    v_is_active BOOLEAN;
BEGIN
    -- Check if coupon_id is provided in the order
    IF NEW.coupon_id IS NULL THEN
        RETURN;
    END IF;

    -- Fetch coupon details
    SELECT discount_percentage, min_purchase, valid_from, valid_until, is_active
    INTO v_discount_percentage, v_min_purchase, v_valid_from, v_valid_until, v_is_active
    FROM coupons
    WHERE id = NEW.coupon_id;

    -- Validate coupon
    IF NOT FOUND OR NOT v_is_active OR NOW() < v_valid_from OR NOW() > v_valid_until THEN
        RAISE NOTICE 'Invalid or expired coupon.';
        RETURN;
    END IF;

    -- Apply discount if min purchase is met
    IF NEW.total_amount >= v_min_purchase THEN
        NEW.total_amount := NEW.total_amount - (NEW.total_amount * (v_discount_percentage / 100));
    ELSE
        RAISE NOTICE 'Minimum purchase not met for coupon.';
    END IF;
END;
$$;
