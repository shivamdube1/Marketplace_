"""
Checkout routes — Razorpay online payment + Cash on Delivery.
"""
import hmac
import hashlib
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, session, request, jsonify, current_app)
from flask_login import current_user
from extensions import db
from models.product import Product
from models.cart import CartItem
from models.order import Order, OrderItem
from forms.checkout_forms import CheckoutForm
from routes.cart import _get_cart, _calc_shipping


# ── State-based auto-assign helper ───────────────────────────────────────────

def _auto_assign_delivery(order):
    """Automatically assign order to the delivery partner for that state."""
    try:
        from models.delivery import DeliveryPartner, DeliveryAssignment
        from models.order import OrderTracking
        from models.user import User

        STATE_PARTNER_EMAIL = {
            'Chhattisgarh':  'rider.cg@fabricbazaar.in',
            'Maharashtra':   'rider@fabricbazaar.in',
            'Karnataka':     'rider.kar@fabricbazaar.in',
            'Goa':           'rider.goa@fabricbazaar.in',
        }

        order_state = (order.state or '').strip()
        email = STATE_PARTNER_EMAIL.get(order_state, 'rider.rest@fabricbazaar.in')

        user = User.query.filter_by(email=email).first()
        if not user:
            return  # partner not seeded yet

        partner = DeliveryPartner.query.filter_by(user_id=user.id).first()
        if not partner:
            return

        # Don't double-assign
        existing = DeliveryAssignment.query.filter(
            DeliveryAssignment.order_id == order.id,
            DeliveryAssignment.status.notin_(['delivered','failed','returned','cancelled'])
        ).first()
        if existing:
            return

        otp = DeliveryAssignment.generate_otp()
        assignment = DeliveryAssignment(
            order_id=order.id,
            partner_id=partner.id,
            status='assigned',
            otp=otp,
        )
        db.session.add(assignment)
        order.status = 'handed_to_courier'
        OrderTracking.log(
            order_id=order.id,
            status='handed_to_courier',
            message=f'Auto-assigned to delivery partner for {order_state or "your region"}. OTP generated for customer.',
        )
        db.session.commit()
    except Exception as e:
        import traceback
        traceback.print_exc()


checkout_bp = Blueprint('checkout', __name__)


def _razorpay_client():
    import razorpay
    return razorpay.Client(auth=(
        current_app.config['RAZORPAY_KEY_ID'],
        current_app.config['RAZORPAY_KEY_SECRET'],
    ))


# ─── Step 1 & 2: Checkout Form ───────────────────────────────────────────────

@checkout_bp.route('/', methods=['GET', 'POST'])
def index():
    cart_items, subtotal = _get_cart()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('shop.index'))

    shipping = _calc_shipping(subtotal)
    tax      = round(float(subtotal) * 0.18, 2)
    total    = float(subtotal) + float(shipping) + float(tax)

    form = CheckoutForm()
    if current_user.is_authenticated and not form.is_submitted():
        form.first_name.data = current_user.first_name
        form.last_name.data  = current_user.last_name
        form.email.data      = current_user.email

    if form.validate_on_submit():
        loyalty_discount = 0.0
        payment_method = request.form.get('payment_method', 'online')

        order = Order(
            order_number   = Order.generate_order_number(),
            user_id        = current_user.id if current_user.is_authenticated else None,
            first_name     = form.first_name.data.strip(),
            last_name      = form.last_name.data.strip(),
            email          = form.email.data.lower().strip(),
            phone          = form.phone.data.strip(),
            address_line1  = form.address_line1.data.strip(),
            address_line2  = (form.address_line2.data or '').strip() or None,
            city           = form.city.data.strip(),
            state          = form.state.data,
            postal_code    = form.postal_code.data.strip(),
            country        = 'India',
            notes          = (form.notes.data or '').strip() or None,
            subtotal       = subtotal,
            shipping_cost  = shipping,
            tax            = tax,
            total          = total,
            status         = Order.STATUS_PENDING,
            payment_status = 'pending',
        )
        db.session.add(order)
        db.session.flush()

        for ci in cart_items:
            product = ci['product']
            db.session.add(OrderItem(
                order_id      = order.id,
                product_id    = product.id,
                product_name  = product.name,
                product_image = product.primary_image,
                price         = product.display_price,
                quantity      = ci['quantity'],
            ))
            p = Product.query.get(product.id)
            if p:
                p.stock = max(0, p.stock - ci['quantity'])

        db.session.commit()
        session['pending_order'] = order.order_number

        # COD → skip payment, go straight to confirmation
        if payment_method == 'cod':
            order.status         = Order.STATUS_CONFIRMED
            order.payment_status = 'cod'
            db.session.commit()
            if current_user.is_authenticated:
                CartItem.query.filter_by(user_id=current_user.id).delete()
            session.pop('cart', None)
            session.pop('pending_order', None)
            db.session.commit()
            _auto_assign_delivery(order)
            flash('Order placed! Pay cash on delivery. A delivery partner has been assigned.', 'success')
            return redirect(url_for('checkout.confirmation',
                                    order_number=order.order_number))

        # Online payment
        return redirect(url_for('checkout.payment',
                                order_number=order.order_number))

    return render_template('checkout.html',
                           form=form,
                           cart_items=cart_items,
                           subtotal=subtotal,
                           shipping=shipping,
                           tax=tax,
                           total=total)


# ─── Payment Page ─────────────────────────────────────────────────────────────

@checkout_bp.route('/payment/<order_number>')
def payment(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    if order.payment_status in ('paid', 'cod'):
        return redirect(url_for('checkout.confirmation',
                                order_number=order.order_number))
    return render_template('payment.html',
                           order=order,
                           razorpay_key=current_app.config['RAZORPAY_KEY_ID'])


# ─── Create Razorpay Order (AJAX) ─────────────────────────────────────────────

@checkout_bp.route('/razorpay/create-order', methods=['POST'])
def create_razorpay_order():
    import razorpay
    data         = request.get_json() or {}
    order_number = data.get('order_number') or session.get('pending_order')
    if not order_number:
        return jsonify({'success': False, 'error': 'Order not found'}), 400
    order = Order.query.filter_by(order_number=order_number).first()
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    if order.razorpay_order_id:
        return jsonify({'success': True, 'rzp_order_id': order.razorpay_order_id,
                        'amount': 100, 'key': current_app.config['RAZORPAY_KEY_ID'],
                        'name': order.full_name, 'email': order.email,
                        'phone': order.phone or ''})
    try:
        client = _razorpay_client()
        rzp_order = client.order.create({
            'amount': 100, 'currency': 'INR',
            'receipt': order.order_number,
            'notes': {'order_number': order.order_number},
            'payment_capture': 1,
        })
        order.razorpay_order_id = rzp_order['id']
        db.session.commit()
        return jsonify({'success': True, 'rzp_order_id': rzp_order['id'],
                        'amount': rzp_order['amount'],
                        'key': current_app.config['RAZORPAY_KEY_ID'],
                        'name': order.full_name, 'email': order.email,
                        'phone': order.phone or ''})
    except Exception as e:
        current_app.logger.error(f'Razorpay error: {e}')
        return jsonify({'success': False, 'error': 'Payment service error'}), 500


# ─── Verify Razorpay Signature (AJAX) ─────────────────────────────────────────

@checkout_bp.route('/payment/verify', methods=['POST'])
def verify_payment():
    data = request.get_json() or {}
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_order_id   = data.get('razorpay_order_id', '')
    razorpay_signature  = data.get('razorpay_signature', '')
    order_number        = data.get('order_number') or session.get('pending_order')

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, order_number]):
        return jsonify({'success': False, 'error': 'Missing payment data'}), 400

    order = Order.query.filter_by(order_number=order_number).first()
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    key_secret   = current_app.config['RAZORPAY_KEY_SECRET'].encode('utf-8')
    message      = f'{razorpay_order_id}|{razorpay_payment_id}'.encode('utf-8')
    expected_sig = hmac.new(key_secret, message, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig, razorpay_signature):
        return jsonify({'success': False, 'error': 'Signature verification failed'}), 400

    order.status              = Order.STATUS_CONFIRMED
    order.payment_status      = 'paid'
    order.razorpay_payment_id = razorpay_payment_id
    order.tracking_number     = razorpay_payment_id
    db.session.commit()
    _auto_assign_delivery(order)

    if current_user.is_authenticated:
        CartItem.query.filter_by(user_id=current_user.id).delete()
    session.pop('cart', None)
    session.pop('pending_order', None)
    db.session.commit()

    return jsonify({'success': True,
                    'redirect': url_for('checkout.confirmation',
                                        order_number=order.order_number)})


# ─── Payment Failed ────────────────────────────────────────────────────────────

@checkout_bp.route('/payment/failed', methods=['POST'])
def payment_failed():
    data         = request.get_json() or {}
    order_number = data.get('order_number') or session.get('pending_order')
    reason       = data.get('reason', 'unknown')
    if order_number:
        order = Order.query.filter_by(order_number=order_number).first()
        if order and order.payment_status == 'pending':
            for item in order.items:
                if item.product_id:
                    p = Product.query.get(item.product_id)
                    if p: p.stock += item.quantity
            order.payment_status = 'failed'
            order.notes = (order.notes or '') + f'\nPayment failed: {reason}'
            db.session.commit()
    return jsonify({'success': True})


# ─── Confirmation ─────────────────────────────────────────────────────────────

@checkout_bp.route('/confirmation/<order_number>')
def confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template('order_confirmation.html', order=order)
