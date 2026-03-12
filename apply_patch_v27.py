"""
FabricBazaar v27 Patch
Run: python apply_patch_v27.py
Fixes: AppenderQuery len() error + auto-assign delivery by state
"""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Fix 1: available_orders.html ─────────────────────────────────────────────
tmpl = os.path.join(BASE, 'templates', 'delivery', 'available_orders.html')
os.makedirs(os.path.dirname(tmpl), exist_ok=True)

with open(tmpl, 'w', encoding='utf-8') as f:
    f.write("""\
{% extends 'base.html' %}
{% block title %}Available Orders{% endblock %}
{% block content %}
<div style="background:#0D3B2E;min-height:100vh;padding-bottom:80px;font-family:'DM Sans',sans-serif;">
  <div style="background:#0D3B2E;padding:1rem 1.1rem;display:flex;align-items:center;gap:.75rem;border-bottom:1px solid rgba(255,255,255,.1);">
    <a href="{{ url_for('delivery.dashboard') }}" style="color:#fff;font-size:1.1rem;text-decoration:none;">←</a>
    <h1 style="color:#fff;font-size:1rem;font-weight:700;margin:0;flex:1;">📦 Available Orders</h1>
    <span style="font-size:.75rem;color:rgba(255,255,255,.6);">{{ orders_with_items|length }} available</span>
  </div>
  <div style="padding:1rem;">
    {% if not orders_with_items %}
    <div style="text-align:center;padding:3rem 1rem;color:rgba(255,255,255,.5);">
      <div style="font-size:3rem;margin-bottom:.75rem;">🎉</div>
      <div style="font-weight:600;font-size:1rem;">No orders available right now</div>
      <div style="font-size:.82rem;margin-top:.4rem;">Check back soon</div>
    </div>
    {% endif %}
    {% for order, items in orders_with_items %}
    <div style="background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:1rem;margin-bottom:.875rem;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.65rem;">
        <div>
          <div style="color:#fff;font-weight:700;font-size:.95rem;">{{ order.order_number }}</div>
          <div style="font-size:.72rem;color:rgba(255,255,255,.5);margin-top:.15rem;">{{ order.created_at.strftime('%d %b · %I:%M %p') }}</div>
        </div>
        <span style="background:{% if order.payment_status=='cod' %}#F59E0B{% else %}#10B981{% endif %};color:#fff;font-size:.68rem;font-weight:700;padding:.25rem .6rem;border-radius:20px;">
          {% if order.payment_status=='cod' %}COD{% else %}PAID{% endif %}
        </span>
      </div>
      <div style="background:rgba(0,0,0,.2);border-radius:8px;padding:.65rem .875rem;margin-bottom:.75rem;">
        <div style="font-size:.68rem;color:rgba(255,255,255,.4);text-transform:uppercase;letter-spacing:.08em;margin-bottom:.25rem;">📍 Deliver to</div>
        <div style="color:#fff;font-size:.84rem;font-weight:600;">{{ order.full_name }}</div>
        <div style="color:rgba(255,255,255,.6);font-size:.78rem;line-height:1.5;margin-top:.15rem;">
          {{ order.address_line1 }}{% if order.address_line2 %}, {{ order.address_line2 }}{% endif %}<br>
          {{ order.city }}, {{ order.state }} — {{ order.postal_code }}
        </div>
      </div>
      <div style="font-size:.78rem;color:rgba(255,255,255,.6);margin-bottom:.75rem;">
        {% for item in items[:2] %}
        <div style="display:flex;justify-content:space-between;padding:.2rem 0;">
          <span>{{ item.product_name[:35] }}{% if item.product_name|length > 35 %}…{% endif %} ×{{ item.quantity }}</span>
          <span>{{ item.subtotal | inr }}</span>
        </div>
        {% endfor %}
        {% if items|length > 2 %}<div style="color:rgba(255,255,255,.35);">+{{ items|length - 2 }} more items</div>{% endif %}
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;gap:.75rem;">
        <div>
          <div style="color:rgba(255,255,255,.5);font-size:.68rem;">Order Total</div>
          <div style="color:#fff;font-weight:800;font-size:1.1rem;">{{ order.total | inr }}</div>
        </div>
        <form method="POST" action="{{ url_for('delivery.claim_order', order_id=order.id) }}"
              onsubmit="return confirm('Claim order {{ order.order_number }}?')">
          <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
          <button type="submit" style="background:#10B981;color:#fff;border:none;border-radius:10px;padding:.65rem 1.25rem;font-size:.85rem;font-weight:700;cursor:pointer;font-family:inherit;">
            🚴 Claim Order
          </button>
        </form>
      </div>
    </div>
    {% endfor %}
  </div>
  <nav style="position:fixed;bottom:0;left:0;right:0;background:#0A2E22;border-top:1px solid rgba(255,255,255,.1);display:flex;z-index:100;">
    {% for icon,label,url in [('🏠','Home',url_for('delivery.dashboard')),('📦','Available',url_for('delivery.available_orders')),('📋','My Orders',url_for('delivery.orders')),('👤','Profile',url_for('delivery.profile'))] %}
    <a href="{{ url }}" style="flex:1;display:flex;flex-direction:column;align-items:center;padding:.6rem .4rem;color:{% if request.endpoint=='delivery.available_orders' and loop.index==2 %}#10B981{% else %}rgba(255,255,255,.5){% endif %};text-decoration:none;font-size:.6rem;gap:.2rem;">
      <span style="font-size:1.1rem;">{{ icon }}</span>{{ label }}
    </a>
    {% endfor %}
  </nav>
</div>
{% endblock %}
""")
print("  ✅  templates/delivery/available_orders.html  — fixed")

# ── Fix 2: routes/delivery.py — pre-load items as list ───────────────────────
delivery_path = os.path.join(BASE, 'routes', 'delivery.py')
content = open(delivery_path, encoding='utf-8').read()

old = "    return render_template('delivery/available_orders.html',\n                           partner=partner, orders=orders)"
new = (
    "    orders_with_items = [(o, o.items.all()) for o in orders]\n"
    "    return render_template('delivery/available_orders.html',\n"
    "                           partner=partner, orders_with_items=orders_with_items)"
)
if old in content:
    content = content.replace(old, new)
    open(delivery_path, 'w', encoding='utf-8').write(content)
    print("  ✅  routes/delivery.py  — items pre-loaded as list")
elif 'orders_with_items' in content:
    print("  ✅  routes/delivery.py  — already patched")
else:
    print("  ⚠️  routes/delivery.py  — pattern not found, check manually")

# ── Fix 3: routes/checkout.py — state-based auto-assign ──────────────────────
checkout_path = os.path.join(BASE, 'routes', 'checkout.py')
content = open(checkout_path, encoding='utf-8').read()

if '_auto_assign_delivery' in content:
    print("  ✅  routes/checkout.py  — auto-assign already present")
else:
    auto_fn = '''
def _auto_assign_delivery(order):
    """Auto-assign order to delivery partner based on customer state."""
    try:
        from models.delivery import DeliveryPartner, DeliveryAssignment
        from models.order import OrderTracking
        from models.user import User
        STATE_MAP = {
            'Chhattisgarh': 'rider.cg@fabricbazaar.in',
            'Maharashtra':  'rider@fabricbazaar.in',
            'Karnataka':    'rider.kar@fabricbazaar.in',
            'Goa':          'rider.goa@fabricbazaar.in',
        }
        email = STATE_MAP.get((order.state or '').strip(), 'rider.rest@fabricbazaar.in')
        user = User.query.filter_by(email=email).first()
        if not user:
            return
        partner = DeliveryPartner.query.filter_by(user_id=user.id).first()
        if not partner:
            return
        existing = DeliveryAssignment.query.filter(
            DeliveryAssignment.order_id == order.id,
            DeliveryAssignment.status.notin_(['delivered','failed','returned','cancelled'])
        ).first()
        if existing:
            return
        assignment = DeliveryAssignment(
            order_id=order.id, partner_id=partner.id,
            status='assigned', otp=DeliveryAssignment.generate_otp(),
        )
        db.session.add(assignment)
        order.status = 'handed_to_courier'
        OrderTracking.log(order_id=order.id, status='handed_to_courier',
            message=f'Auto-assigned to delivery partner for {order.state or "your region"}.')
        db.session.commit()
    except Exception:
        import traceback; traceback.print_exc()

'''
    content = content.replace('checkout_bp = Blueprint', auto_fn + 'checkout_bp = Blueprint')

    # Hook into COD path
    content = content.replace(
        "flash('Order placed! Pay cash on delivery.', 'success')",
        "_auto_assign_delivery(order)\n            flash('Order placed! Pay cash on delivery.', 'success')"
    )
    # Hook into online payment verified path
    content = content.replace(
        "order.tracking_number     = razorpay_payment_id\n    db.session.commit()\n",
        "order.tracking_number     = razorpay_payment_id\n    db.session.commit()\n    _auto_assign_delivery(order)\n"
    )
    open(checkout_path, 'w', encoding='utf-8').write(content)
    print("  ✅  routes/checkout.py  — auto-assign by state added")

print("\n✅  Patch complete! Restart: python app.py")
