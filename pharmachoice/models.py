from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, default="customer")
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    gender = db.Column(db.String(20), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    pincode = db.Column(db.String(20), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=False)

    orders = db.relationship("Order", back_populates="user", cascade="all, delete-orphan")


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    drugs = db.relationship("Drug", back_populates="category", cascade="all, delete-orphan")


class Drug(db.Model):
    __tablename__ = "drugs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    discount_percent = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = db.relationship("Category", back_populates="drugs")
    orders = db.relationship("Order", back_populates="drug")

    @property
    def final_price(self):
        discount_ratio = max(0.0, min(self.discount_percent, 100.0)) / 100
        return round(self.base_price * (1 - discount_ratio), 2)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    drug_id = db.Column(db.Integer, db.ForeignKey("drugs.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Order Placed")
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="orders")
    drug = db.relationship("Drug", back_populates="orders")
