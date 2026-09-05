from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Order, OrderItem, Coupon, Payment
from cart.models import Cart
from core.models import Notification
from django.conf import settings
import hmac, hashlib
import stripe
try:
    import razorpay
except Exception:
    razorpay = None


@login_required
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or cart.items.count() == 0:
        return redirect("cart_view")

    total = cart.get_total()
    
    if request.method == "POST":
        code = request.POST.get("coupon") or ""
        delivery_name = request.POST.get("delivery_name")
        delivery_phone = request.POST.get("delivery_phone")
        delivery_address = request.POST.get("delivery_address")
        
        discount = 0
        applied_coupon = None
        if code:
            c = Coupon.objects.filter(code=code, active=True).first()
            if c:
                if c.type == "percent":
                    discount = total * (c.value / 100)
                else:
                    discount = c.value
                if discount > total:
                    discount = total
                applied_coupon = c

        is_service = any(item.service for item in cart.items.all())

        order = Order.objects.create(
            user=request.user, 
            total_amount=total - discount,
            delivery_name=delivery_name,
            delivery_phone=delivery_phone,
            delivery_address=delivery_address,
            is_service_order=is_service
        )
        
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                service=item.service,
                quantity=item.quantity,
                price=item.get_unit_price()
            )

        cart.items.all().delete()

        if applied_coupon:
            applied_coupon.used_count = (applied_coupon.used_count or 0) + 1
            applied_coupon.save()

        # Default to COD/Pending for this simplified flow
        Payment.objects.create(user=request.user, provider="cod", amount=order.total_amount, order=order, status="pending")
        Notification.objects.create(user=request.user, title="Order placed", body=f"Order #{order.id} created")
        
        return redirect("order_detail", order_id=order.id)
    
    return redirect("cart_view")



@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    payment = Payment.objects.filter(order=order).order_by("-id").first()
    return render(request, "orders/order_success.html", {"order": order, "payment": payment})


@login_required
def invoice_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        import os
        from django.conf import settings as django_settings
    except Exception:
        return HttpResponse("PDF generation library missing", status=500)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # --- Draw Header Decoration ---
    p.saveState()
    p.setFillColor(colors.HexColor('#f0f4ff'))
    p.rect(0, h - 1.5*inch, w, 1.5*inch, fill=1, stroke=0)
    p.restoreState()

    # --- Logo (Professional Branding) ---
    logo_path = os.path.join(django_settings.BASE_DIR, 'static', 'image', 'logo.jpeg')
    if os.path.exists(logo_path):
        # Position logo professionally at top left
        p.drawImage(logo_path, 0.5*inch, h - 1*inch, width=1.6*inch, height=0.6*inch, mask='auto', preserveAspectRatio=True)
    
    # --- Invoice Title ---
    p.setFont("Helvetica-Bold", 32)
    p.setFillColor(colors.HexColor('#324bc9'))
    p.drawRightString(w - 0.5*inch, h - 0.8*inch, "INVOICE")
    
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.black)
    p.drawRightString(w - 0.5*inch, h - 1.05*inch, f"Order #{order.id:04d}")
    p.drawRightString(w - 0.5*inch, h - 1.2*inch, f"Date: {order.created_at.strftime('%d %b, %Y')}")

    # --- Bill To & Ship To ---
    y_info = h - 2*inch
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(colors.HexColor('#324bc9'))
    p.drawString(0.5*inch, y_info, "BILL TO")
    p.drawString(3.5*inch, y_info, "SHIP TO")
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    # Bill To
    p.drawString(0.5*inch, y_info - 15, order.user.get_full_name() or order.user.username)
    p.drawString(0.5*inch, y_info - 30, order.user.email)
    
    # Ship To
    p.drawString(3.5*inch, y_info - 15, order.delivery_name or order.user.username)
    p.drawString(3.5*inch, y_info - 30, order.delivery_phone or "-")
    p.drawString(3.5*inch, y_info - 45, order.delivery_address or "-")

    # --- Group Items by Store ---
    items_by_store = {}
    for item in order.items.all():
        store = None
        if item.product and item.product.store:
            store = item.product.store
        elif item.service and item.service.store:
            store = item.service.store
        
        store_id = store.id if store else 0
        if store_id not in items_by_store:
            items_by_store[store_id] = {'store': store, 'items': []}
        items_by_store[store_id]['items'].append(item)

    # --- Table Header ---
    y = y_info - 0.8*inch
    p.setStrokeColor(colors.HexColor('#324bc9'))
    p.setLineWidth(1.5)
    p.line(0.5*inch, y, w - 0.5*inch, y)
    
    y -= 20
    p.setFont("Helvetica-Bold", 10)
    p.drawString(0.6*inch, y, "QTY")
    p.drawString(1.4*inch, y, "DESCRIPTION")
    p.drawRightString(w - 1.6*inch, y, "UNIT PRICE")
    p.drawRightString(w - 0.6*inch, y, "TOTAL")
    
    y -= 10
    p.setLineWidth(0.5)
    p.line(0.5*inch, y, w - 0.5*inch, y)

    # --- Render Grouped Items ---
    total_items_amount = 0
    for store_id, data in items_by_store.items():
        store = data['store']
        items = data['items']
        
        y -= 25
        # Check for new page
        if y < 1.5*inch:
            p.showPage()
            y = h - 1*inch
            
        # Store Header
        p.setFillColor(colors.HexColor('#f8f9fa'))
        p.rect(0.5*inch, y - 5, w - 1*inch, 18, fill=1, stroke=0)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 10)
        store_display = store.name if store else "Local Khoj Items"
        p.drawString(0.6*inch, y, f"Store: {store_display}")
        if store and store.address:
            p.setFont("Helvetica-Oblique", 8)
            p.drawRightString(w - 0.6*inch, y, store.address[:80])
        
        y -= 20
        p.setFont("Helvetica", 10)
        for item in items:
            # Check for new page
            if y < 1*inch:
                p.showPage()
                y = h - 1*inch
                
            name = item.product.name if item.product else item.service.name
            p.drawString(0.6*inch, y, str(item.quantity))
            p.drawString(1.4*inch, y, name)
            p.drawRightString(w - 1.6*inch, y, f"{item.price:,.2f}")
            p.drawRightString(w - 0.6*inch, y, f"{item.get_total_price():,.2f}")
            total_items_amount += item.get_total_price()
            y -= 18

    # --- Footer Totals ---
    y -= 20
    p.setLineWidth(1)
    p.line(w - 3*inch, y, w - 0.5*inch, y)
    
    y -= 20
    p.setFont("Helvetica", 10)
    p.drawRightString(w - 1.6*inch, y, "Subtotal:")
    p.drawRightString(w - 0.6*inch, y, f"₹ {total_items_amount:,.2f}")
    
    discount = total_items_amount - order.total_amount
    if discount > 0:
        y -= 15
        p.drawRightString(w - 1.6*inch, y, "Discount:")
        p.drawRightString(w - 0.6*inch, y, f"- ₹ {discount:,.2f}")
        
    y -= 25
    p.setFont("Helvetica-Bold", 14)
    p.setFillColor(colors.HexColor('#324bc9'))
    p.drawRightString(w - 1.6*inch, y, "GRAND TOTAL:")
    p.drawRightString(w - 0.6*inch, y, f"₹ {order.total_amount:,.2f}")

    # --- Terms & Branding ---
    p.setFont("Helvetica-Bold", 10)
    p.drawString(0.5*inch, 1.2*inch, "TERMS & CONDITIONS")
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.black)
    p.drawString(0.5*inch, 1.05*inch, "1. Payment is due within 15 days of order placement.")
    p.drawString(0.5*inch, 0.9*inch, "2. This is a computer-generated invoice and requires no signature.")
    p.drawString(0.5*inch, 0.75*inch, "Thank you for shopping with Local Khoj!")

    p.showPage()
    p.save()

    buffer.seek(0)
    resp = HttpResponse(buffer.read(), content_type="application/pdf")
    resp['Content-Disposition'] = f'inline; filename="invoice_{order.id}.pdf"'
    return resp


@login_required
def pay_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    key_id = getattr(settings, "RAZORPAY_KEY_ID", None)
    stripe_pk = getattr(settings, "STRIPE_PUBLISHABLE_KEY", None)
    amount_paise = int(float(order.total_amount) * 100)
    razorpay_order = None
    if razorpay and key_id and getattr(settings, "RAZORPAY_KEY_SECRET", None):
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": str(order.id),
            "payment_capture": 1
        })
    return render(
        request,
        "orders/pay.html",
        {
            "order": order,
            "amount_paise": amount_paise,
            "key_id": key_id,
            "stripe_pk": stripe_pk,
            "razorpay_order_id": (razorpay_order or {}).get("id"),
        }
    )


@login_required
def pay_verify(request):
    if request.method != "POST":
        return redirect("home")
    order_id = request.POST.get("order_id")
    payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    signature = request.POST.get("razorpay_signature")
    order = get_object_or_404(Order, id=order_id, user=request.user)

    secret = getattr(settings, "RAZORPAY_KEY_SECRET", None)
    key_id = getattr(settings, "RAZORPAY_KEY_ID", None)
    status = "failed"
    if razorpay and secret and key_id and payment_id and razorpay_order_id and signature:
        try:
            client = razorpay.Client(auth=(key_id, secret))
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            })
            status = "completed"
        except Exception:
            status = "failed"
    if status == "completed":
        Payment.objects.create(user=request.user, provider="razorpay", amount=order.total_amount, order=order, status="completed")
        Notification.objects.create(user=request.user, title="Payment successful", body=f"Order #{order.id}")
    else:
        Payment.objects.create(user=request.user, provider="razorpay", amount=order.total_amount, order=order, status="failed")
        Notification.objects.create(user=request.user, title="Payment failed", body=f"Order #{order.id}")
    return redirect("order_detail", order_id=order.id)


@login_required
def pay_stripe_create(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    secret = getattr(settings, "STRIPE_SECRET_KEY", None)
    pk = getattr(settings, "STRIPE_PUBLISHABLE_KEY", None)
    if not secret or not pk:
        return redirect("order_detail", order_id=order.id)
    stripe.api_key = secret
    success_url = request.build_absolute_uri(f"/orders/pay/stripe/complete/?order_id={order.id}&session_id={{CHECKOUT_SESSION_ID}}")
    cancel_url = request.build_absolute_uri(f"/orders/order/{order.id}/")
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "inr",
                "product_data": {"name": f"Order #{order.id}"},
                "unit_amount": int(float(order.total_amount) * 100),
            },
            "quantity": 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(order.id),
        customer_email=request.user.email or None,
    )
    return render(request, "orders/stripe_redirect.html", {"session_id": session.id, "stripe_pk": pk})


@login_required
def pay_stripe_complete(request):
    secret = getattr(settings, "STRIPE_SECRET_KEY", None)
    stripe.api_key = secret or ""
    session_id = request.GET.get("session_id")
    order_id = request.GET.get("order_id")
    order = get_object_or_404(Order, id=order_id, user=request.user)
    status = "failed"
    try:
        if session_id and secret:
            sess = stripe.checkout.Session.retrieve(session_id)
            if sess.get("payment_status") == "paid":
                status = "completed"
    except Exception:
        status = "failed"
    Payment.objects.create(user=request.user, provider="stripe", amount=order.total_amount, order=order, status=status)
    Notification.objects.create(user=request.user, title=("Payment successful" if status=="completed" else "Payment failed"), body=f"Order #{order.id}")
    return redirect("order_detail", order_id=order.id)


def pay_stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    event = None
    if not endpoint_secret:
        return HttpResponse(status=400)
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception:
        return HttpResponse(status=400)
    if event["type"] == "checkout.session.completed":
        sess = event["data"]["object"]
        order_id = sess.get("client_reference_id")
        user = request.user if request.user.is_authenticated else None
        try:
            order = Order.objects.get(id=int(order_id))
            Payment.objects.create(user=order.user, provider="stripe", amount=order.total_amount, order=order, status="completed")
            Notification.objects.create(user=order.user, title="Payment successful", body=f"Order #{order.id}")
        except Exception:
            pass
    return HttpResponse(status=200)
