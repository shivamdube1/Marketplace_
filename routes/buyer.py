"""
Buyer dashboard — order history, order detail with tracking timeline,
and account settings. (Loyalty points removed)
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models.order import Order
from models.wishlist import WishlistItem
from models.messaging import MessageThread

buyer_bp = Blueprint('buyer', __name__)


def _require_customer():
    if not current_user.is_customer:
        flash('Customer account required.', 'warning')
        return redirect(url_for('main.index'))


# ── Dashboard ──────────────────────────────────────────────────────────────────

@buyer_bp.route('/account')
@login_required
def dashboard():
    r = _require_customer()
    if r: return r
    orders = current_user.orders.order_by(Order.created_at.desc()).limit(5).all()
    unread = db.session.query(db.func.sum(MessageThread.unread_customer)).filter_by(
        customer_id=current_user.id).scalar() or 0
    wishlist_count = WishlistItem.query.filter_by(user_id=current_user.id).count()
    return render_template('buyer/dashboard.html',
                           orders=orders, unread=int(unread),
                           wishlist_count=wishlist_count)


# ── Orders ─────────────────────────────────────────────────────────────────────

@buyer_bp.route('/account/orders')
@login_required
def orders():
    r = _require_customer()
    if r: return r
    page = request.args.get('page', 1, type=int)
    all_orders = (current_user.orders
                  .order_by(Order.created_at.desc())
                  .paginate(page=page, per_page=10, error_out=False))
    return render_template('buyer/orders.html', orders=all_orders)


# ── Order Detail + Tracking ────────────────────────────────────────────────────

@buyer_bp.route('/account/orders/<order_number>')
@login_required
def order_detail(order_number):
    r = _require_customer()
    if r: return r
    order = Order.query.filter_by(
        order_number=order_number, user_id=current_user.id).first_or_404()
    timeline = _build_timeline(order)
    return render_template('buyer/order_detail.html', order=order, timeline=timeline)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_timeline(order):
    STATUS_STEPS = [
        ('pending',    '🛒', 'Order Placed',      'Your order has been received'),
        ('confirmed',  '✅', 'Payment Confirmed',  'Payment verified successfully'),
        ('processing', '⚙️', 'Being Prepared',     'Seller is preparing your order'),
        ('shipped',    '🚚', 'Out for Delivery',   'Your order is on its way'),
        ('delivered',  '📦', 'Delivered',          'Order successfully delivered'),
    ]
    current_status = order.status
    status_order = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
    try:
        current_idx = status_order.index(current_status)
    except ValueError:
        current_idx = -1

    timeline = []
    for i, (status, icon, label, desc) in enumerate(STATUS_STEPS):
        if current_status == 'cancelled':
            state = 'cancelled' if status == 'pending' else 'pending'
        elif current_status == 'refunded':
            state = 'done' if status == 'pending' else ('refunded' if status == 'confirmed' else 'pending')
        else:
            state = 'done' if i < current_idx else ('active' if i == current_idx else 'pending')
        timeline.append({'status': status, 'icon': icon, 'label': label,
                         'desc': desc, 'state': state,
                         'time': order.created_at if status == 'pending' else None})

    if current_status == 'cancelled':
        timeline.append({'status': 'cancelled', 'icon': '❌', 'label': 'Cancelled',
                         'desc': 'This order has been cancelled',
                         'state': 'cancelled', 'time': order.updated_at})
    elif current_status == 'refunded':
        timeline.append({'status': 'refunded', 'icon': '💸', 'label': 'Refunded',
                         'desc': 'Refund has been processed',
                         'state': 'done', 'time': order.updated_at})
    return timeline
