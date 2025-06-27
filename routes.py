import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import os
from flask import render_template, request, redirect, url_for, flash, jsonify, session, send_file, Response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, func, desc

from app import app, db
from models import (User, Product, Category, CartItem, Order, OrderItem, 
                    WishlistItem, Review, Notification, Log, ExpiryAlert, Coupon)
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, BooleanField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from forms import (LoginForm, RegistrationForm, ProductForm, CheckoutForm, 
                   ReviewForm, PasswordResetForm, ProfileUpdateForm)
from utils.gemini_ai import get_ai_response, check_medical_interactions
from utils.geocoding import get_coordinates_from_address
from utils.sms_service import send_order_status_sms
from utils.pdf_generator import generate_invoice_pdf
from sqlalchemy import text

def log_admin_login(user_id, details):
    db.session.execute(
        text("CALL admin_login_log(:uid, :details)"),
        {'uid': user_id, 'details': details}
    )
    db.session.commit()

def customer_login_login(user_id, details):
    db.session.execute(
        text("CALL customer_login_log(:uid, :details)"),
        {'uid': user_id, 'details': details}
    )
    db.session.commit()

def cart_update(p_item_id, qty):
    db.session.execute(
        text("CALL update_or_remove_cart_item(:item_id, :quantity)"),
        {'item_id': p_item_id, 'quantity': qty}
    )
    db.session.commit()


def register_routes(app):
    # Admin required decorator
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function

    # Log user action
    def log_action(action, details=None):
        user_id = current_user.id if current_user.is_authenticated else None
        # Create log entry without positional arguments
        log = Log()
        log.user_id = user_id
        log.action = action
        log.details = details
        db.session.add(log)
        db.session.commit()

    # Home page
    @app.route('/')
    def index():
        # Get featured products (discounted items)
        featured_products = Product.query.filter(Product.original_price != None).limit(6).all()
        
        # Get some grocery and pharmacy products
        grocery_products = Product.query.join(Category).filter(Category.is_pharmacy == False).limit(6).all()
        pharmacy_products = Product.query.join(Category).filter(Category.is_pharmacy == True).limit(6).all()
        
        return render_template('index.html', 
                            featured_products=featured_products,
                            grocery_products=grocery_products,
                            pharmacy_products=pharmacy_products)

    # Authentication routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                if user.is_admin:
                    log_admin_login(user.id, f'Admin {user.username} logged in')
                    return redirect(url_for('admin_dashboard'))
                else:
                    customer_login_login(user.id, f'User {user.username} logged in')
                    return redirect(url_for('index'))
            flash('Invalid email or password', 'danger')
        
        return render_template('auth/login.html', form=form)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        
        form = RegistrationForm()
        if form.validate_on_submit():
            # Create user without positional arguments
            user = User()
            user.username = form.username.data
            user.email = form.email.data
            user.phone = form.phone.data
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            # Create a welcome notification
            notification = Notification()
            notification.user_id = user.id
            notification.message = "Welcome to SmartCartPro! Start shopping for groceries and medicines with our smart platform."
            db.session.add(notification)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        return render_template('auth/register.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        log_action('logout', f'User {current_user.username} logged out')
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    # Product routes
    @app.route('/products')
    def products():
        category_id = request.args.get('category', type=int)
        search_query = request.args.get('q', '')
        sort_by = request.args.get('sort', 'name')
        is_pharmacy = request.args.get('pharmacy', type=int)
        
        # Base query
        query = Product.query
        
        # Apply filters
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if is_pharmacy is not None:
            query = query.join(Category).filter(Category.is_pharmacy == bool(is_pharmacy))
        
        if search_query:
            query = query.filter(
                or_(
                    Product.name.ilike(f'%{search_query}%'),
                    Product.description.ilike(f'%{search_query}%')
                )
            )
        
        # Apply sorting
        if sort_by == 'price_low':
            query = query.order_by(Product.price)
        elif sort_by == 'price_high':
            query = query.order_by(Product.price.desc())
        elif sort_by == 'newest':
            query = query.order_by(Product.created_at.desc())
        else:  # default to name
            query = query.order_by(Product.name)
        
        # Get all categories for the filter sidebar
        categories = Category.query.all()
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 12
        products = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('customer/products.html', 
                            products=products,
                            categories=categories,
                            current_category=category_id,
                            search_query=search_query,
                            sort_by=sort_by,
                            is_pharmacy=is_pharmacy)

    @app.route('/product/<int:product_id>')
    def product_detail(product_id):
        product = Product.query.get_or_404(product_id)
        reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
        
        # Get related products in the same category
        related_products = Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product.id
        ).limit(4).all()
        
        # Get user's review if they've made one
        user_review = None
        if current_user.is_authenticated:
            user_review = Review.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).first()
        
        review_form = ReviewForm()
        
        return render_template('customer/product_detail.html',
                            product=product,
                            reviews=reviews,
                            review_form=review_form,
                            user_review=user_review,
                            related_products=related_products)

    # Cart routes
    @app.route('/cart')
    @login_required
    def view_cart():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        # Calculate cart total
        total = sum(item.total_price() for item in cart_items)
        
        # Get applicable coupons
        coupons = Coupon.query.filter(
            Coupon.is_active == True,
            Coupon.valid_from <= datetime.utcnow(),
            Coupon.valid_until >= datetime.utcnow(),
            Coupon.min_purchase <= total
        ).all()
        
        # Get applied coupon if exists
        applied_coupon = None
        if session.get('applied_coupon'):
            applied_coupon = Coupon.query.get(session['applied_coupon'])
        
        return render_template('customer/cart.html', 
                            cart_items=cart_items,
                            total=total,
                            coupons=coupons,
                            coupon=applied_coupon)

    @app.route('/cart/add/<int:product_id>', methods=['POST'])
    @login_required
    def add_to_cart(product_id):
        product = Product.query.get_or_404(product_id)
        quantity = int(request.form.get('quantity', 1))
        
        if quantity <= 0:
            flash('Invalid quantity.', 'danger')
            return redirect(url_for('product_detail', product_id=product_id))
        
        if product.stock < quantity:
            flash(f'Sorry, only {product.stock} items available in stock.', 'warning')
            return redirect(url_for('product_detail', product_id=product_id))
        
        # Check if product is already in cart
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            # Update quantity if already in cart
            cart_item.quantity += quantity
            db.session.commit()
            flash(f'Updated quantity of {product.name} in your cart.', 'success')
        else:
            # Add new item to cart
            cart_item = CartItem()
            cart_item.user_id = current_user.id
            cart_item.product_id = product_id
            cart_item.quantity = quantity
            db.session.add(cart_item)
            db.session.commit()
            flash(f'Added {product.name} to your cart.', 'success')
        
        log_action('add_to_cart', f'Added {quantity} of product #{product_id} to cart')
        
        return redirect(url_for('view_cart'))

    @app.route('/cart/update/<int:item_id>', methods=['POST'])
    @login_required
    def update_cart_item(item_id):
        cart_item = CartItem.query.get_or_404(item_id)
        
        # Ensure the cart item belongs to the current user
        if cart_item.user_id != current_user.id:
            flash('You do not have permission to modify this cart item.', 'danger')
            return redirect(url_for('view_cart'))
        
        quantity = int(request.form.get('quantity', 1))
        
        if quantity <= 0:
            # Remove item if quantity is 0 or negative
            db.session.delete(cart_item)
            db.session.commit()
            flash('Item removed from cart.', 'info')
        else:
            # Check stock availability
            if cart_item.product.stock < quantity:
                flash(f'Sorry, only {cart_item.product.stock} items available in stock.', 'warning')
                return redirect(url_for('view_cart'))
            
            # Update quantity
            cart_item.quantity = quantity
            db.session.commit()
            flash('Cart updated.', 'success')
        
        log_action('update_cart', f'Updated cart item #{item_id} quantity to {quantity}')
        
        return redirect(url_for('view_cart'))


    @app.route('/cart/remove/<int:item_id>', methods=['POST'])
    @login_required
    def remove_from_cart(item_id):
        cart_item = CartItem.query.get_or_404(item_id)
        
        # Ensure the cart item belongs to the current user
        if cart_item.user_id != current_user.id:
            flash('You do not have permission to modify this cart item.', 'danger')
            return redirect(url_for('view_cart'))
        
        db.session.delete(cart_item)
        db.session.commit()
        
        flash('Item removed from cart.', 'info')
        log_action('remove_from_cart', f'Removed item #{item_id} from cart')
        
        return redirect(url_for('view_cart'))

    # Checkout routes
    @app.route('/checkout', methods=['GET', 'POST'])
    @login_required
    def checkout():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        if not cart_items:
            flash('Your cart is empty.', 'info')
            return redirect(url_for('products'))
        
        # Calculate cart total
        total = sum(item.total_price() for item in cart_items)
        
        # Check stock availability before proceeding
        for item in cart_items:
            if item.product.stock < item.quantity:
                flash(f'Sorry, only {item.product.stock} items of {item.product.name} available in stock.', 'warning')
                return redirect(url_for('view_cart'))
        
        form = CheckoutForm()
        
        # Apply coupon if provided
        coupon_code = request.form.get('coupon_code')
        discount = 0
        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code).first()
            if coupon and coupon.is_valid() and total >= coupon.min_purchase:
                discount = total * (coupon.discount_percentage / 100)
                total -= discount
                session['applied_coupon'] = coupon.id
            else:
                flash('Invalid or expired coupon code.', 'danger')
        
        if form.validate_on_submit():
            # Create a new order
            order = Order()
            order.user_id = current_user.id
            order.total_amount = total
            order.delivery_address = form.address.data
            
            # Get coordinates for the address
            if form.address.data:
                try:
                    lat, lng = get_coordinates_from_address(str(form.address.data))
                    order.delivery_latitude = lat
                    order.delivery_longitude = lng
                except Exception as e:
                    logging.error(f"Geocoding error: {str(e)}")
                    # Continue without coordinates if geocoding fails
            
            db.session.add(order)
            db.session.flush()  # Get order ID
            
            # Create order items and update stock
            for cart_item in cart_items:
                order_item = OrderItem()
                order_item.order_id = order.id
                order_item.product_id = cart_item.product_id
                order_item.quantity = cart_item.quantity
                order_item.price = cart_item.product.price
                db.session.add(order_item)
                
                # Update product stock
                product = cart_item.product
                product.stock -= cart_item.quantity
                
                # Remove from cart
                db.session.delete(cart_item)
            
            db.session.commit()
            
            # Send order confirmation SMS
            try:
                if current_user.phone:
                    send_order_status_sms(current_user.phone, 'confirmed', order.id)
            except Exception as e:
                logging.error(f"SMS sending error: {str(e)}")
            
            # Create notification for order
            notification = Notification()
            notification.user_id = current_user.id
            notification.message = f"Your order #{order.id} has been confirmed. We'll notify you when it ships."
            db.session.add(notification)
            db.session.commit()
            
            log_action('place_order', f'Placed order #{order.id} with {len(order.items)} items')
            
            flash('Order placed successfully!', 'success')
            return redirect(url_for('order_complete', order_id=order.id))
        
        return render_template('customer/checkout.html', 
                            form=form, 
                            cart_items=cart_items, 
                            total=total,
                            discount=discount)

    @app.route('/order/complete/<int:order_id>')
    @login_required
    def order_complete(order_id):
        order = Order.query.get_or_404(order_id)
        
        # Ensure the order belongs to the current user
        if order.user_id != current_user.id:
            flash('You do not have permission to view this order.', 'danger')
            return redirect(url_for('orders'))
        
        return render_template('customer/order_complete.html', order=order)

    # Order routes
    @app.route('/orders')
    @login_required
    def orders():
        user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        return render_template('customer/orders.html', user_orders=user_orders)

    @app.route('/order/<int:order_id>')
    @login_required
    def order_detail(order_id):
        order = Order.query.get_or_404(order_id)
        
        # Ensure the order belongs to the current user
        if order.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to view this order.', 'danger')
            return redirect(url_for('orders'))
        
        return render_template('customer/order_detail.html', order=order)

    @app.route('/order/<int:order_id>/reorder', methods=['POST'])
    @login_required
    def reorder(order_id):
        order = Order.query.get_or_404(order_id)
        
        # Ensure the order belongs to the current user
        if order.user_id != current_user.id:
            flash('You do not have permission to reorder this order.', 'danger')
            return redirect(url_for('orders'))
        
        # Clear current cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        
        # Add order items to cart
        for item in order.items:
            product = Product.query.get(item.product_id)
            if product and product.stock > 0:
                # Adjust quantity to available stock if needed
                quantity = min(item.quantity, product.stock)
                
                cart_item = CartItem()
                cart_item.user_id = current_user.id
                cart_item.product_id = item.product_id
                cart_item.quantity = quantity
                db.session.add(cart_item)
        
        db.session.commit()
        log_action('reorder', f'Reordered from order #{order_id}')
        
        flash('Items from your previous order have been added to your cart.', 'success')
        return redirect(url_for('view_cart'))

    # Wishlist routes
    @app.route('/wishlist')
    @login_required
    def wishlist():
        wishlist_items = WishlistItem.query.filter_by(user_id=current_user.id).all()
        return render_template('customer/wishlist.html', wishlist_items=wishlist_items)

    @app.route('/wishlist/add/<int:product_id>', methods=['POST'])
    @login_required
    def add_to_wishlist(product_id):
        # Check if product exists
        product = Product.query.get_or_404(product_id)
        
        # Check if already in wishlist
        existing_item = WishlistItem.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if existing_item:
            flash('This product is already in your wishlist.', 'info')
        else:
            wishlist_item = WishlistItem()
            wishlist_item.user_id = current_user.id
            wishlist_item.product_id = product_id
            db.session.add(wishlist_item)
            db.session.commit()
            log_action('add_to_wishlist', f'Added product #{product_id} to wishlist')
            flash('Product added to your wishlist.', 'success')
        
        return redirect(url_for('product_detail', product_id=product_id))

    @app.route('/wishlist/remove/<int:item_id>', methods=['POST'])
    @login_required
    def remove_from_wishlist(item_id):
        wishlist_item = WishlistItem.query.get_or_404(item_id)
        
        # Ensure the wishlist item belongs to the current user
        if wishlist_item.user_id != current_user.id:
            flash('You do not have permission to modify this wishlist item.', 'danger')
            return redirect(url_for('wishlist'))
        
        db.session.delete(wishlist_item)
        db.session.commit()
        
        log_action('remove_from_wishlist', f'Removed item #{item_id} from wishlist')
        flash('Item removed from your wishlist.', 'info')
        
        return redirect(url_for('wishlist'))

    @app.route('/wishlist/move-to-cart/<int:item_id>', methods=['POST'])
    @login_required
    def move_to_cart(item_id):
        wishlist_item = WishlistItem.query.get_or_404(item_id)
        
        # Ensure the wishlist item belongs to the current user
        if wishlist_item.user_id != current_user.id:
            flash('You do not have permission to modify this wishlist item.', 'danger')
            return redirect(url_for('wishlist'))
        
        # Check if product is already in cart
        product_id = wishlist_item.product_id
        cart_item = CartItem.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if cart_item:
            # Update quantity if already in cart
            cart_item.quantity += 1
        else:
            # Add new item to cart
            cart_item = CartItem()
            cart_item.user_id = current_user.id
            cart_item.product_id = product_id
            cart_item.quantity = 1
            db.session.add(cart_item)
        
        # Remove from wishlist
        db.session.delete(wishlist_item)
        db.session.commit()
        
        log_action('move_to_cart', f'Moved wishlist item #{item_id} to cart')
        flash('Item moved to your cart.', 'success')
        
        return redirect(url_for('wishlist'))

    # Review routes
    @app.route('/product/<int:product_id>/review', methods=['POST'])
    @login_required
    def add_review(product_id):
        product = Product.query.get_or_404(product_id)
        
        # Check if user has purchased this product
        has_purchased = OrderItem.query.join(Order).filter(
            Order.user_id == current_user.id,
            OrderItem.product_id == product_id,
            Order.status == 'delivered'
        ).first() is not None
        
        if not has_purchased and not current_user.is_admin:
            flash('You can only review products you have purchased.', 'warning')
            return redirect(url_for('product_detail', product_id=product_id))
        
        form = ReviewForm()
        
        if form.validate_on_submit():
            # Check if user already has a review for this product
            existing_review = Review.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).first()
            
            if existing_review:
                # Update existing review
                existing_review.rating = form.rating.data
                existing_review.comment = form.comment.data
                flash('Your review has been updated.', 'success')
            else:
                # Create new review
                review = Review()
                review.user_id = current_user.id
                review.product_id = product_id
                review.rating = form.rating.data
                review.comment = form.comment.data
                db.session.add(review)
                flash('Your review has been submitted.', 'success')
            
            db.session.commit()
            log_action('add_review', f'Added/updated review for product #{product_id}')
            
        return redirect(url_for('product_detail', product_id=product_id))

    # Invoice routes
    @app.route('/order/<int:order_id>/invoice')
    @login_required
    def view_invoice(order_id):
        order = Order.query.get_or_404(order_id)
        
        # Ensure the order belongs to the current user
        if order.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to view this invoice.', 'danger')
            return redirect(url_for('orders'))
        
        return render_template('customer/invoice.html', order=order)

    @app.route('/order/<int:order_id>/invoice/pdf')
    @login_required
    def download_invoice_pdf(order_id):
        order = Order.query.get_or_404(order_id)
        
        # Ensure the order belongs to the current user
        if order.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to download this invoice.', 'danger')
            return redirect(url_for('orders'))
        
        # Generate PDF
        pdf_path = generate_invoice_pdf(order)
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            download_name=f'invoice_order_{order.id}.pdf',
            as_attachment=True
        )

    # AI Chatbot routes
    @app.route('/api/ai/chat', methods=['POST'])
    @login_required
    def ai_chat():
        data = request.json or {}
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        try:
            response = get_ai_response(query)
            log_action('ai_chat', f'Query: {query[:50]}...')
            return jsonify({'response': response})
        except Exception as e:
            logging.error(f"AI chatbot error: {str(e)}")
            return jsonify({'error': 'Failed to get response from AI service'}), 500

    @app.route('/api/ai/medical-interaction', methods=['POST'])
    def check_medical_interaction():
        data = request.json or {}
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({'error': 'Product IDs are required'}), 400
        
        try:
            products = Product.query.filter(Product.id.in_(product_ids)).all()
            warnings = check_medical_interactions(products)
            return jsonify({'warnings': warnings})
        except Exception as e:
            logging.error(f"Medical interaction check error: {str(e)}")
            return jsonify({'error': 'Failed to check medical interactions'}), 500

    # Notification routes
    @app.route('/notifications')
    @login_required
    def notifications():
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.created_at.desc()).all()
        
        # Mark notifications as read
        for notification in user_notifications:
            notification.read = True
        
        db.session.commit()
        
        return render_template('customer/notifications.html', notifications=user_notifications)

    @app.route('/api/notifications/unread')
    @login_required
    def unread_notifications_count():
        count = Notification.query.filter_by(
            user_id=current_user.id,
            read=False
        ).count()
        
        return jsonify({'count': count})

    # Admin routes
    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        # Recent orders
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        
        # Order statistics
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        delivered_orders = Order.query.filter_by(status='delivered').count()
        
        # Revenue statistics
        today = datetime.utcnow().date()
        daily_revenue = db.session.query(func.sum(Order.total_amount)).filter(
            func.date(Order.created_at) == today
        ).scalar() or 0
        
        # Start of the month
        first_day = today.replace(day=1)
        monthly_revenue = db.session.query(func.sum(Order.total_amount)).filter(
            func.date(Order.created_at) >= first_day
        ).scalar() or 0
        
        # Total revenue
        total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
        
        # Stock alerts
        low_stock_count = Product.query.filter(Product.stock < 10).count()
        low_stock_products = Product.query.filter(Product.stock < 10).limit(5).all()
        
        # Expiry alerts
        thirty_days_later = datetime.utcnow().date() + timedelta(days=30)
        expiry_alert_count = Product.query.filter(
            Product.expiry_date <= thirty_days_later,
            Product.expiry_date >= today,
            Product.stock > 0
        ).count()
        
        expiring_products = Product.query.filter(
            Product.expiry_date <= thirty_days_later,
            Product.expiry_date >= today,
            Product.stock > 0
        ).limit(5).all()
        
        # Sales chart data (last 30 days)
        sales_dates = []
        sales_amounts = []
        
        for i in range(30, -1, -1):
            date = today - timedelta(days=i)
            sales_dates.append(date.strftime('%Y-%m-%d'))
            
            daily_amount = db.session.query(func.sum(Order.total_amount)).filter(
                func.date(Order.created_at) == date
            ).scalar() or 0
            
            sales_amounts.append(float(daily_amount))
        
        # Category distribution data
        categories = Category.query.all()
        category_names = [category.name for category in categories]
        category_counts = [Product.query.filter_by(category_id=category.id).count() for category in categories]
        
        # Pending order count for badge
        pending_order_count = pending_orders
        
        return render_template('admin/dashboard.html',
                            recent_orders=recent_orders,
                            total_orders=total_orders,
                            pending_orders=pending_orders,
                            delivered_orders=delivered_orders,
                            daily_revenue=daily_revenue,
                            monthly_revenue=monthly_revenue,
                            total_revenue=total_revenue,
                            low_stock_count=low_stock_count,
                            low_stock_products=low_stock_products,
                            expiry_alert_count=expiry_alert_count,
                            expiring_products=expiring_products,
                            sales_dates=sales_dates,
                            sales_amounts=sales_amounts,
                            category_names=category_names,
                            category_counts=category_counts,
                            pending_order_count=pending_order_count,
                            today=today)

    @app.route('/admin/inventory')
    @login_required
    @admin_required
    def admin_inventory():
        category_id = request.args.get('category', type=int)
        search_query = request.args.get('q', '')
        
        # Base query
        query = Product.query
        
        # Apply filters
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        if search_query:
            query = query.filter(
                or_(
                    Product.name.ilike(f'%{search_query}%'),
                    Product.description.ilike(f'%{search_query}%')
                )
            )
        
        # Get all categories for the filter
        categories = Category.query.all()
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        products = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('admin/inventory.html',
                            products=products,
                            categories=categories,
                            current_category=category_id,
                            search_query=search_query)

    @app.route('/admin/product/add', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def add_product():
        form = ProductForm()
        # Load categories before validation
        categories = Category.query.all()
        form.category_id.choices = [(c.id, c.name) for c in categories]
        
        if form.validate_on_submit():
            product = Product()
            product.name = form.name.data
            product.description = form.description.data
            product.price = form.price.data
            product.original_price = form.original_price.data if form.original_price.data else None
            product.stock = form.stock.data
            product.category_id = form.category_id.data
            
            # Handle image upload
            if form.image.data:
                image = form.image.data
                # Generate unique filename
                filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{image.filename}")
                # Save file
                image_path = os.path.join(app.static_folder, 'uploads', filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
                product.image_url = f'/static/uploads/{filename}'
            
            product.expiry_date = form.expiry_date.data
            product.medical_warnings = form.medical_warnings.data
            
            db.session.add(product)
            db.session.commit()
            
            if product.expiry_date:
                # Create expiry alert if expiry date is within 90 days
                ninety_days_later = datetime.utcnow().date() + timedelta(days=90)
                if product.expiry_date <= ninety_days_later:
                    expiry_alert = ExpiryAlert()
                    expiry_alert.product_id = product.id
                    expiry_alert.expiry_date = product.expiry_date
                    db.session.add(expiry_alert)
                    db.session.commit()
            
            log_action('add_product', f'Added new product: {product.name}')
            
            flash('Product added successfully.', 'success')
            return redirect(url_for('admin_inventory'))
        
        return render_template('admin/product_form.html', form=form, title='Add Product')

    @app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def edit_product(product_id):
        product = Product.query.get_or_404(product_id)
        form = ProductForm(obj=product)
        form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
        
        if form.validate_on_submit():
            product.name = form.name.data
            product.description = form.description.data
            product.price = form.price.data
            product.original_price = form.original_price.data if form.original_price.data else None
            product.stock = form.stock.data
            product.category_id = form.category_id.data
            product.image_url = form.image_url.data
            product.expiry_date = form.expiry_date.data
            product.medical_warnings = form.medical_warnings.data
            
            db.session.commit()
            
            # Check if this is a discount update
            if product.has_discount():
                # Create notifications for users who have this product in their wishlist
                wishlist_users = db.session.query(WishlistItem.user_id).filter_by(product_id=product.id).distinct().all()
                for user_id in wishlist_users:
                    notification = Notification()
                    notification.user_id = user_id[0]
                    notification.message = f"Good news! {product.name} is now on sale with {product.discount_percentage()}% off."
                    db.session.add(notification)
                
                db.session.commit()
            
            log_action('edit_product', f'Updated product: {product.name}')
            
            flash('Product updated successfully.', 'success')
            return redirect(url_for('admin_inventory'))
        
        return render_template('admin/product_form.html', form=form, product=product, title='Edit Product')

    @app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
    @login_required
    @admin_required
    def delete_product(product_id):
        product = Product.query.get_or_404(product_id)
        
        # Delete related items first
        CartItem.query.filter_by(product_id=product_id).delete()
        WishlistItem.query.filter_by(product_id=product_id).delete()
        ExpiryAlert.query.filter_by(product_id=product_id).delete()
        
        # Remember product name for log
        product_name = product.name
        
        db.session.delete(product)
        db.session.commit()
        
        log_action('delete_product', f'Deleted product: {product_name}')
        
        flash('Product deleted successfully.', 'success')
        return redirect(url_for('admin_inventory'))

    @app.route('/admin/categories')
    @login_required
    @admin_required
    def admin_categories():
        categories = Category.query.all()
        return render_template('admin/categories.html', categories=categories)

    @app.route('/admin/category/add', methods=['POST'])
    @login_required
    @admin_required
    def add_category():
        name = request.form.get('name')
        description = request.form.get('description')
        is_pharmacy = request.form.get('is_pharmacy') == 'on'
        
        if not name:
            flash('Category name is required.', 'danger')
            return redirect(url_for('admin_categories'))
        
        category = Category()
        category.name = name
        category.description = description
        category.is_pharmacy = is_pharmacy
        
        db.session.add(category)
        db.session.commit()
        
        log_action('add_category', f'Added new category: {name}')
        
        flash('Category added successfully.', 'success')
        return redirect(url_for('admin_categories'))

    @app.route('/admin/orders')
    @login_required
    @admin_required
    def admin_orders():
        status = request.args.get('status', '')
        search_query = request.args.get('q', '')
        
        # Base query
        query = Order.query
        
        # Apply filters
        if status:
            query = query.filter_by(status=status)
        
        if search_query:
            try:
                order_id = int(search_query)
                query = query.filter_by(id=order_id)
            except ValueError:
                # If not a number, search by customer username
                query = query.join(User).filter(User.username.ilike(f'%{search_query}%'))
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('admin/orders.html',
                            orders=orders,
                            current_status=status,
                            search_query=search_query)

    @app.route('/admin/order/<int:order_id>')
    @login_required
    @admin_required
    def admin_order_detail(order_id):
        order = Order.query.get_or_404(order_id)
        return render_template('admin/order_detail.html', order=order)

    @app.route('/admin/order/<int:order_id>/status', methods=['POST'])
    @login_required
    @admin_required
    def update_order_status(order_id):
        order = Order.query.get_or_404(order_id)
        new_status = request.form.get('status')
        
        if new_status not in ['pending', 'out_for_delivery', 'delivered', 'cancelled']:
            flash('Invalid status.', 'danger')
            return redirect(url_for('admin_order_detail', order_id=order_id))
        
        # Update status
        old_status = order.status
        order.status = new_status
        db.session.commit()
        
        # Create notification
        status_messages = {
            'pending': 'Your order is being processed.',
            'out_for_delivery': 'Your order is out for delivery!',
            'delivered': 'Your order has been delivered. Enjoy!',
            'cancelled': 'Your order has been cancelled.'
        }
        
        notification = Notification()
        notification.user_id = order.user_id
        notification.message = f"Order #{order.id} update: {status_messages[new_status]}"
        db.session.add(notification)
        db.session.commit()
        
        # Send SMS notification
        try:
            customer = User.query.get(order.user_id)
            if customer and customer.phone:
                send_order_status_sms(customer.phone, new_status, order.id)
        except Exception as e:
            logging.error(f"SMS sending error: {str(e)}")
        
        log_action('update_order_status', f'Updated order #{order_id} status from {old_status} to {new_status}')
        
        flash(f'Order status updated to {new_status}.', 'success')
        return redirect(url_for('admin_order_detail', order_id=order_id))

    @app.route('/admin/delivery')
    @login_required
    @admin_required
    def admin_delivery():
        # Get all orders with delivery coordinates
        orders = Order.query.filter(
            Order.delivery_latitude.isnot(None),
            Order.delivery_longitude.isnot(None)
        ).order_by(Order.created_at.desc()).all()
        
        return render_template('admin/delivery.html', orders=orders)

    @app.route('/admin/logs')
    @login_required
    @admin_required
    def admin_logs():
        page = request.args.get('page', 1, type=int)
        per_page = 50
        logs = Log.query.order_by(Log.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        return render_template('admin/logs.html', logs=logs)

    @app.route('/admin/coupons')
    @login_required
    @admin_required
    def admin_coupons():
        class CouponForm(FlaskForm):
            code = StringField('Coupon Code', validators=[DataRequired()])
            discount_percentage = FloatField('Discount Percentage', validators=[DataRequired(), NumberRange(min=0, max=100)])
            min_purchase = FloatField('Minimum Purchase', validators=[DataRequired(), NumberRange(min=0)])
            valid_from = DateField('Valid From', format='%Y-%m-%d', validators=[DataRequired()])
            valid_until = DateField('Valid Until', format='%Y-%m-%d', validators=[DataRequired()])
            is_active = BooleanField('Active')
            submit = SubmitField('Add Coupon')

        form = CouponForm()
        coupons = Coupon.query.all()
        return render_template('admin/coupons.html', form=form, coupons=coupons)

    @app.route('/admin/coupon/add', methods=['POST'])
    @login_required
    @admin_required
    def add_coupon():
        code = request.form.get('code')
        discount_percentage = float(request.form.get('discount_percentage', 0))
        
        # Handle the date string safely
        valid_until_str = request.form.get('valid_until', '')
        if valid_until_str:
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d')
        else:
            # Default to 30 days from now if no date provided
            valid_until = datetime.utcnow() + timedelta(days=30)
            
        min_purchase = float(request.form.get('min_purchase', 0))
        
        if not code:
            flash('Coupon code is required.', 'danger')
            return redirect(url_for('admin_coupons'))
        
        # Check if code already exists
        existing_coupon = Coupon.query.filter_by(code=code).first()
        if existing_coupon:
            flash('Coupon code already exists.', 'danger')
            return redirect(url_for('admin_coupons'))
        
        coupon = Coupon()
        coupon.code = code
        coupon.discount_percentage = discount_percentage
        coupon.valid_until = valid_until
        coupon.min_purchase = min_purchase
        
        db.session.add(coupon)
        db.session.commit()
        
        log_action('add_coupon', f'Added new coupon: {code}')
        
        flash('Coupon added successfully.', 'success')
        return redirect(url_for('admin_coupons'))

    @app.route('/admin/coupon/<int:coupon_id>/toggle', methods=['POST'])
    @login_required
    @admin_required
    def toggle_coupon(coupon_id):
        coupon = Coupon.query.get_or_404(coupon_id)
        coupon.is_active = not coupon.is_active
        db.session.commit()
        
        status = 'activated' if coupon.is_active else 'deactivated'
        log_action('toggle_coupon', f'{status} coupon: {coupon.code}')
        
        flash(f'Coupon {status}.', 'success')
        return redirect(url_for('admin_coupons'))

    @app.route('/admin/expiry-alerts')
    @login_required
    @admin_required
    def admin_expiry_alerts():
        from datetime import datetime
        today = datetime.utcnow().date()
        alerts = ExpiryAlert.query.filter_by(status='active').order_by(ExpiryAlert.expiry_date).all()
        return render_template('admin/expiry_alerts.html', alerts=alerts, today=today)

    # API routes for AJAX
    @app.route('/api/products/medical-warnings/<int:product_id>')
    def get_medical_warnings(product_id):
        product = Product.query.get_or_404(product_id)
        return jsonify({
            'warnings': product.medical_warnings or 'No specific warnings for this product.'
        })
