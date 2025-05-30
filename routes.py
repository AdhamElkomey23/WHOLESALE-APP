from flask import render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import app, db
from models import User, Order, ProductType
from forms import LoginForm, OrderForm, ProductTypeForm
from utils import generate_invoice_pdf, export_data_csv
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import json

@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard', brand='URBRAND'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard/<brand>')
@login_required
def dashboard(brand):
    if brand not in ['URBRAND', 'SURVACCI']:
        brand = 'URBRAND'
    
    # Get orders for the selected brand
    orders = Order.query.filter_by(brand=brand).all()
    
    # Calculate analytics
    total_revenue = sum(order.revenue for order in orders)
    total_cost = sum(order.cost for order in orders)
    total_profit = total_revenue - total_cost
    
    # Top selling products
    product_sales = {}
    for order in orders:
        product_name = order.product_type_obj.name if order.product_type_obj else "Unknown"
        if product_name in product_sales:
            product_sales[product_name] += order.total_pieces
        else:
            product_sales[product_name] = order.total_pieces
    
    top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return render_template('dashboard.html', 
                         brand=brand,
                         total_revenue=total_revenue,
                         total_cost=total_cost,
                         total_profit=total_profit,
                         top_products=top_products,
                         orders_count=len(orders))

@app.route('/api/sales-chart/<brand>')
@login_required
def sales_chart_data(brand):
    """API endpoint for sales chart data"""
    if brand not in ['URBRAND', 'SURVACCI']:
        return jsonify({'error': 'Invalid brand'}), 400
    
    # Get sales data for the last 12 months
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)
    
    orders = Order.query.filter(
        Order.brand == brand,
        Order.date >= start_date,
        Order.date <= end_date
    ).all()
    
    # Group by month
    monthly_sales = {}
    for order in orders:
        month_key = order.date.strftime('%Y-%m')
        if month_key not in monthly_sales:
            monthly_sales[month_key] = 0
        monthly_sales[month_key] += order.revenue
    
    # Fill in missing months with 0
    current_date = start_date.replace(day=1)
    labels = []
    data = []
    
    while current_date <= end_date:
        month_key = current_date.strftime('%Y-%m')
        labels.append(current_date.strftime('%b %Y'))
        data.append(monthly_sales.get(month_key, 0))
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    return jsonify({
        'labels': labels,
        'data': data
    })

@app.route('/orders')
@login_required
def orders():
    page = request.args.get('page', 1, type=int)
    brand_filter = request.args.get('brand', '')
    
    query = Order.query
    if brand_filter:
        query = query.filter_by(brand=brand_filter)
    
    # Auto-sort by date (newest first)
    orders = query.order_by(Order.date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('orders.html', orders=orders, brand_filter=brand_filter)

@app.route('/orders/new', methods=['GET', 'POST'])
@login_required
def new_order():
    form = OrderForm()
    if form.validate_on_submit():
        order = Order(
            client_name=form.client_name.data,
            phone_number=form.phone_number.data,
            date=form.date.data,
            product_type_id=form.product_type_id.data,
            total_pieces=form.total_pieces.data,
            number_of_colors=form.number_of_colors.data,
            pieces_per_color=form.pieces_per_color.data,
            is_printed=form.is_printed.data,
            paid_amount=form.paid_amount.data,
            remaining_amount=form.remaining_amount.data,
            brand=form.brand.data
        )
        db.session.add(order)
        db.session.commit()
        flash('Order created successfully!', 'success')
        return redirect(url_for('orders'))
    
    return render_template('order_form.html', form=form, title='New Order')

@app.route('/orders/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_order(id):
    order = Order.query.get_or_404(id)
    form = OrderForm(obj=order)
    
    if form.validate_on_submit():
        form.populate_obj(order)
        db.session.commit()
        flash('Order updated successfully!', 'success')
        return redirect(url_for('orders'))
    
    return render_template('order_form.html', form=form, title='Edit Order', order=order)

@app.route('/orders/<int:id>/delete', methods=['POST'])
@login_required
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    flash('Order deleted successfully!', 'success')
    return redirect(url_for('orders'))

@app.route('/orders/<int:id>/invoice')
@login_required
def generate_invoice(id):
    order = Order.query.get_or_404(id)
    pdf_data = generate_invoice_pdf(order)
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{order.id}.pdf'
    
    return response

@app.route('/products')
@login_required
def products():
    products = ProductType.query.all()
    return render_template('products.html', products=products)

@app.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    form = ProductTypeForm()
    if form.validate_on_submit():
        product = ProductType(
            name=form.name.data,
            cost_price=form.cost_price.data,
            selling_price=form.selling_price.data
        )
        db.session.add(product)
        db.session.commit()
        flash('Product created successfully!', 'success')
        return redirect(url_for('products'))
    
    return render_template('products.html', form=form, products=ProductType.query.all())

@app.route('/products/<int:id>/edit', methods=['POST'])
@login_required
def edit_product(id):
    product = ProductType.query.get_or_404(id)
    form = ProductTypeForm()
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.cost_price = form.cost_price.data
        product.selling_price = form.selling_price.data
        db.session.commit()
        flash('Product updated successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('products'))

@app.route('/products/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    product = ProductType.query.get_or_404(id)
    
    # Check if product is used in any orders
    if product.orders:
        flash('Cannot delete product as it is used in existing orders!', 'danger')
    else:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    
    return redirect(url_for('products'))

@app.route('/export')
@login_required
def export():
    return render_template('export.html')

@app.route('/export/csv')
@login_required
def export_csv():
    brand = request.args.get('brand', '')
    csv_data = export_data_csv(brand)
    
    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv'
    filename = f'{brand}_data.csv' if brand else 'all_data.csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

@app.route('/storage')
@login_required
def storage():
    """Storage management page"""
    from models import ProductType, Inventory
    
    # Get all products
    products = ProductType.query.all()
    
    # Get inventory data for both storage types
    shared_inventory = {}
    aziz_inventory = {}
    
    for product in products:
        # Get shared storage (URBRAND + SURVACCI)
        shared_stock = Inventory.query.filter_by(
            product_type_id=product.id,
            storage_type='SHARED'
        ).first()
        shared_inventory[product.id] = shared_stock.quantity if shared_stock else 0
        
        # Get AZIZ storage
        aziz_stock = Inventory.query.filter_by(
            product_type_id=product.id,
            storage_type='AZIZ'
        ).first()
        aziz_inventory[product.id] = aziz_stock.quantity if aziz_stock else 0
    
    return render_template('storage.html',
                         products=products,
                         shared_inventory=shared_inventory,
                         aziz_inventory=aziz_inventory)

@app.route('/storage/adjust', methods=['POST'])
@login_required
def adjust_stock():
    """Adjust stock levels"""
    from models import Inventory, StockMovement
    
    product_id = int(request.form.get('product_id'))
    storage_type = request.form.get('storage_type')
    adjustment_type = request.form.get('adjustment_type')
    quantity = int(request.form.get('quantity', 0))
    notes = request.form.get('notes', '')
    
    try:
        # Get or create inventory record
        inventory = Inventory.query.filter_by(
            product_type_id=product_id,
            storage_type=storage_type
        ).first()
        
        if not inventory:
            inventory = Inventory(
                product_type_id=product_id,
                storage_type=storage_type,
                quantity=0
            )
            db.session.add(inventory)
        
        # Apply adjustment
        if adjustment_type == 'ADD':
            inventory.quantity += quantity
        elif adjustment_type == 'REMOVE':
            if inventory.quantity >= quantity:
                inventory.quantity -= quantity
            else:
                flash(f'Not enough stock to remove {quantity} items. Current stock: {inventory.quantity}', 'error')
                return redirect(url_for('storage'))
        
        inventory.updated_at = datetime.utcnow()
        
        # Create stock movement record
        movement = StockMovement(
            product_type_id=product_id,
            storage_type=storage_type,
            movement_type=adjustment_type,
            quantity=quantity,
            notes=notes,
            created_by=current_user.id
        )
        db.session.add(movement)
        
        db.session.commit()
        flash(f'Stock {adjustment_type.lower()}ed successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating stock: {str(e)}', 'error')
    
    return redirect(url_for('storage'))
