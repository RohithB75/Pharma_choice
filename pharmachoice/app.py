import os
from functools import wraps
from urllib.parse import quote_plus

from flask import Flask, flash, redirect, render_template, request, session, url_for
from sqlalchemy import text

from models import Category, Drug, Order, User, db


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("PHARMACHOICE_SECRET_KEY", "replace_with_a_secure_secret_key")
configured_db_uri = os.getenv("PHARMACHOICE_DB_URI")
if not configured_db_uri:
    db_user = os.getenv("PHARMACHOICE_DB_USER", "root")
    db_password = quote_plus(os.getenv("PHARMACHOICE_DB_PASSWORD", ""))
    db_host = os.getenv("PHARMACHOICE_DB_HOST", "localhost")
    db_port = os.getenv("PHARMACHOICE_DB_PORT", "3306")
    db_name = os.getenv("PHARMACHOICE_DB_NAME", "pharmachoice_db")
    configured_db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

app.config["SQLALCHEMY_DATABASE_URI"] = configured_db_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def initialize_default_admin():
    if User.query.count() == 0:
        admin = User(
            role="admin",
            name="System Admin",
            email="admin@gmail.com",
            password_hash="123",
            phone="0000000000",
            address="Head Office",
        )
        db.session.add(admin)
        db.session.commit()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def get_cart():
    cart = session.get("cart", {})
    if not isinstance(cart, dict):
        cart = {}
    return cart


@app.context_processor
def inject_common_context():
    cart = get_cart()
    cart_count = sum(cart.values()) if cart else 0
    return {"cart_count": cart_count}


@app.route("/")
def index():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    if session.get("role") == "customer":
        return redirect(url_for("user_dashboard"))
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender", "").strip()
        age = request.form.get("age", "").strip()
        pincode = request.form.get("pincode", "").strip()
        state = request.form.get("state", "").strip()
        address = request.form.get("address", "").strip()
        password = request.form.get("password", "")

        if not all([name, email, phone, gender, address, password]):
            flash("Name, email, phone, gender, address, and password are required.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email is already registered.", "warning")
            return redirect(url_for("register"))

        try:
            age = int(age) if age else None
        except ValueError:
            age = None

        user = User(
            role="customer",
            name=name,
            email=email,
            phone=phone,
            gender=gender,
            age=age,
            pincode=pincode,
            state=state,
            address=address,
            password_hash=password,
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or user.password_hash != password:
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        session["role"] = user.role
        session["user_name"] = user.name

        flash("Welcome back!", "success")
        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():
    selected_section = request.args.get("section", "dashboard")
    allowed_sections = {"dashboard", "add_category", "view_category", "add_drug", "view_drugs", "view_orders"}
    if selected_section not in allowed_sections:
        selected_section = "dashboard"

    category_filter = request.args.get("category_id", "").strip()
    search_drug_name = request.args.get("q", "").strip()
    sort_option = request.args.get("sort", "az").strip().lower()

    low_stock_drugs = Drug.query.filter(Drug.stock < 10).order_by(Drug.stock.asc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    drugs_query = Drug.query
    if category_filter.isdigit():
        drugs_query = drugs_query.filter(Drug.category_id == int(category_filter))
    if search_drug_name:
        drugs_query = drugs_query.filter(Drug.name.ilike(f"%{search_drug_name}%"))

    if sort_option == "za":
        drugs_query = drugs_query.order_by(Drug.name.desc())
    elif sort_option == "price_low":
        drugs_query = drugs_query.order_by(Drug.base_price.asc())
    elif sort_option == "price_high":
        drugs_query = drugs_query.order_by(Drug.base_price.desc())
    else:
        sort_option = "az"
        drugs_query = drugs_query.order_by(Drug.name.asc())

    drugs = drugs_query.all()
    orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template(
        "admin_dash.html",
        active_section=selected_section,
        current_category_filter=category_filter,
        current_drug_query=search_drug_name,
        current_sort_option=sort_option,
        low_stock_drugs=low_stock_drugs,
        categories=categories,
        drugs=drugs,
        orders=orders,
    )


@app.route("/admin/category/add", methods=["POST"])
@login_required
@role_required("admin")
def add_category():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("admin_dashboard", section="add_category"))

    existing = Category.query.filter(db.func.lower(Category.name) == name.lower()).first()
    if existing:
        flash("Category already exists.", "warning")
        return redirect(url_for("admin_dashboard", section="add_category"))

    category = Category(name=name)
    db.session.add(category)
    db.session.commit()
    flash("Category added successfully.", "success")
    return redirect(url_for("admin_dashboard", section="add_category"))


@app.route("/admin/category/<int:category_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)

    linked_drug = Drug.query.filter_by(category_id=category.id).first()
    if linked_drug:
        flash("Cannot delete category because it is linked to one or more drugs.", "warning")
        return redirect(url_for("admin_dashboard", section="view_category"))

    db.session.delete(category)
    db.session.commit()
    flash("Category deleted successfully.", "success")
    return redirect(url_for("admin_dashboard", section="view_category"))


@app.route("/admin/drug/add", methods=["POST"])
@login_required
@role_required("admin")
def add_drug():
    try:
        name = request.form.get("name", "").strip()
        category_id = int(request.form.get("category_id", "0"))
        base_price = float(request.form.get("base_price", "0"))
        discount_percent = float(request.form.get("discount_percent", "0"))
        stock = int(request.form.get("stock", "0"))
    except ValueError:
        flash("Please provide valid numeric values for drug details.", "danger")
        return redirect(url_for("admin_dashboard", section="add_drug"))

    if not name or category_id <= 0:
        flash("Drug name and category are required.", "danger")
        return redirect(url_for("admin_dashboard", section="add_drug"))

    if base_price < 0 or stock < 0 or discount_percent < 0 or discount_percent > 100:
        flash("Price/discount/stock values are out of range.", "danger")
        return redirect(url_for("admin_dashboard", section="add_drug"))

    category = Category.query.get(category_id)
    if not category:
        flash("Selected category does not exist.", "danger")
        return redirect(url_for("admin_dashboard", section="add_drug"))

    drug = Drug(
        name=name,
        category_id=category_id,
        base_price=base_price,
        discount_percent=discount_percent,
        stock=stock,
    )
    db.session.add(drug)
    db.session.commit()
    flash("Drug added successfully.", "success")
    return redirect(url_for("admin_dashboard", section="add_drug"))


@app.route("/admin/drug/<int:drug_id>/update", methods=["GET", "POST"])
@login_required
@role_required("admin")
def update_drug(drug_id):
    drug = Drug.query.get_or_404(drug_id)

    if request.method == "GET":
        return render_template("update_drug.html", drug=drug, category_name=drug.category.name)

    try:
        name = request.form.get("name", "").strip()
        base_price = float(request.form.get("base_price", drug.base_price))
        discount_percent = float(request.form.get("discount_percent", drug.discount_percent))
        stock = int(request.form.get("stock", drug.stock))
    except ValueError:
        flash("Invalid update values.", "danger")
        return redirect(url_for("admin_dashboard", section="view_drugs"))

    if not name:
        flash("Drug name is required.", "danger")
        return redirect(url_for("update_drug", drug_id=drug.id))

    if base_price < 0 or stock < 0 or discount_percent < 0 or discount_percent > 100:
        flash("Updated values are out of range.", "danger")
        return redirect(url_for("admin_dashboard", section="view_drugs"))

    drug.name = name
    drug.base_price = base_price
    drug.discount_percent = discount_percent
    drug.stock = stock
    db.session.commit()
    flash(f"Updated drug: {drug.name}", "success")
    return redirect(url_for("admin_dashboard", section="view_drugs"))


@app.route("/admin/drug/<int:drug_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_drug(drug_id):
    drug = Drug.query.get_or_404(drug_id)

    linked_order = Order.query.filter_by(drug_id=drug.id).first()
    if linked_order:
        flash("Cannot delete drug because it exists in order history.", "warning")
        return redirect(url_for("admin_dashboard", section="view_drugs"))

    db.session.delete(drug)
    db.session.commit()
    flash(f"Deleted drug: {drug.name}", "success")
    return redirect(url_for("admin_dashboard", section="view_drugs"))


@app.route("/admin/order/<int:order_id>/status", methods=["POST"])
@login_required
@role_required("admin")
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status", "Order Placed")

    if new_status not in {"Order Placed", "Shipped", "Delivered"}:
        flash("Invalid order status.", "danger")
        return redirect(url_for("admin_dashboard", section="view_orders"))

    order.status = new_status
    db.session.commit()
    flash(f"Order #{order.id} status updated.", "success")
    return redirect(url_for("admin_dashboard", section="view_orders"))


@app.route("/dashboard")
@login_required
@role_required("customer")
def user_dashboard():
    search_term = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", "").strip()
    sort_option = request.args.get("sort", "az").strip().lower()

    query = Drug.query.filter(Drug.stock > 0)
    if search_term:
        query = query.filter(Drug.name.ilike(f"%{search_term}%"))
    if category_id.isdigit():
        query = query.filter(Drug.category_id == int(category_id))

    if sort_option == "za":
        query = query.order_by(Drug.name.desc())
    elif sort_option == "price_low":
        query = query.order_by(Drug.base_price.asc())
    elif sort_option == "price_high":
        query = query.order_by(Drug.base_price.desc())
    else:
        sort_option = "az"
        query = query.order_by(Drug.name.asc())

    drugs = query.all()
    categories = Category.query.order_by(Category.name.asc()).all()
    orders = (
        Order.query.filter_by(user_id=session["user_id"])
        .order_by(Order.order_date.desc())
        .all()
    )

    return render_template(
        "user_dash.html",
        drugs=drugs,
        categories=categories,
        current_q=search_term,
        current_category_id=category_id,
        current_sort_option=sort_option,
        orders=orders,
    )


@app.route("/cart")
@login_required
@role_required("customer")
def view_cart():
    cart = get_cart()
    cart_items = []
    grand_total = 0.0

    for drug_id_str, qty in cart.items():
        if qty <= 0:
            continue
        drug = Drug.query.get(int(drug_id_str))
        if not drug:
            continue

        line_total = round(drug.final_price * qty, 2)
        grand_total += line_total
        cart_items.append(
            {
                "drug": drug,
                "quantity": qty,
                "line_total": line_total,
            }
        )

    return render_template("cart.html", cart_items=cart_items, grand_total=round(grand_total, 2))


@app.route("/orders")
@login_required
@role_required("customer")
def my_orders():
    orders = (
        Order.query.filter_by(user_id=session["user_id"])
        .order_by(Order.order_date.desc())
        .all()
    )
    return render_template("orders.html", orders=orders)


@app.route("/cart/add/<int:drug_id>", methods=["POST"])
@login_required
@role_required("customer")
def add_to_cart(drug_id):
    drug = Drug.query.get_or_404(drug_id)

    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        flash("Quantity must be a valid number.", "danger")
        return redirect(url_for("user_dashboard"))

    if quantity <= 0:
        flash("Quantity should be at least 1.", "warning")
        return redirect(url_for("user_dashboard"))

    cart = get_cart()
    current_qty = cart.get(str(drug_id), 0)
    requested_total = current_qty + quantity

    if requested_total > drug.stock:
        flash(f"Only {drug.stock} units of {drug.name} are available.", "danger")
        return redirect(url_for("user_dashboard"))

    cart[str(drug_id)] = requested_total
    session["cart"] = cart
    flash(f"Added {quantity} x {drug.name} to cart.", "success")
    return redirect(url_for("user_dashboard"))


@app.route("/cart/update/<int:drug_id>", methods=["POST"])
@login_required
@role_required("customer")
def update_cart_item(drug_id):
    cart = get_cart()
    key = str(drug_id)

    if key not in cart:
        flash("Item not found in cart.", "warning")
        return redirect(url_for("view_cart"))

    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        flash("Quantity must be a valid number.", "danger")
        return redirect(url_for("view_cart"))

    if quantity <= 0:
        cart.pop(key, None)
        session["cart"] = cart
        flash("Item removed from cart.", "info")
        return redirect(url_for("view_cart"))

    drug = Drug.query.get_or_404(drug_id)
    if quantity > drug.stock:
        flash(f"Cannot set quantity above available stock ({drug.stock}).", "danger")
        return redirect(url_for("view_cart"))

    cart[key] = quantity
    session["cart"] = cart
    return redirect(url_for("view_cart"))


@app.route("/cart/remove/<int:drug_id>", methods=["POST"])
@login_required
@role_required("customer")
def remove_cart_item(drug_id):
    cart = get_cart()
    removed = cart.pop(str(drug_id), None)
    session["cart"] = cart

    if removed is None:
        flash("Item was not in cart.", "warning")
    else:
        flash("Item removed from cart.", "info")
    return redirect(url_for("view_cart"))


@app.route("/cart/confirm", methods=["POST"])
@login_required
@role_required("customer")
def confirm_order():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("view_cart"))

    current_user = User.query.get(session.get("user_id"))
    if not current_user:
        session.clear()
        flash("Your session is no longer valid. Please log in again.", "warning")
        return redirect(url_for("login"))

    legacy_user_data = {
        "id": current_user.id,
        "role": current_user.role,
        "name": current_user.name,
        "email": current_user.email,
        "password_hash": current_user.password_hash,
        "phone": current_user.phone,
        "address": current_user.address,
    }
    legacy_user_exists = db.session.execute(
        text("SELECT id FROM `user` WHERE id = :id"),
        {"id": current_user.id},
    ).first()
    if legacy_user_exists:
        db.session.execute(
            text(
                "UPDATE `user` SET role = :role, name = :name, email = :email, password_hash = :password_hash, phone = :phone, address = :address WHERE id = :id"
            ),
            legacy_user_data,
        )
    else:
        db.session.execute(
            text(
                "INSERT INTO `user` (id, role, name, email, password_hash, phone, address) VALUES (:id, :role, :name, :email, :password_hash, :phone, :address)"
            ),
            legacy_user_data,
        )

    selected_drugs = []
    for drug_id_str, qty in cart.items():
        if qty <= 0:
            continue
        drug = Drug.query.get(int(drug_id_str))
        if not drug:
            flash("A cart item no longer exists. Please review your cart.", "danger")
            return redirect(url_for("view_cart"))
        if qty > drug.stock:
            flash(f"Insufficient stock for {drug.name}. Available: {drug.stock}.", "danger")
            return redirect(url_for("view_cart"))
        selected_drugs.append((drug, qty))

    if not selected_drugs:
        flash("No valid items found in cart.", "warning")
        return redirect(url_for("view_cart"))

    for drug, qty in selected_drugs:
        order = Order(
            user_id=session["user_id"],
            drug_id=drug.id,
            quantity=qty,
            total_price=round(drug.final_price * qty, 2),
            status="Order Placed",
        )
        drug.stock -= qty
        db.session.add(order)

    db.session.commit()
    session["cart"] = {}
    flash("Order confirmed successfully.", "success")
    return redirect(url_for("view_cart"))


with app.app_context():
    db.create_all()
    initialize_default_admin()


if __name__ == "__main__":
    app.run(debug=True)
