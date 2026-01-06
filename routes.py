from flask import render_template, redirect, url_for, flash, request, jsonify, make_response, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from app import app, db, csrf
from models import User, Order, ProductType, Inventory, StockMovement, Worker, WorkerAttendance, Client, OrderItem, ColorSizeInventory, MoneyTransfer
from forms import LoginForm, OrderForm, ProductTypeForm, UserProfileForm, WorkerForm, AttendanceForm, AttendanceFilterForm, ClientForm, ColorSizeInventoryForm, MoneyTransferForm
from utils import generate_invoice_pdf, export_data_csv
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import json

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You do not have permission to access this feature.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """Home page with brand overview and performance indicators"""
    # Clear welcome flag after first visit
    show_welcome = session.pop('show_welcome', False)
    from models import Expense
    
    # Calculate performance for each brand
    brands_data = {}
    
    for brand in ['URBRAND', 'SURVACCI', 'AZIZ']:
        # Get orders and expenses for this brand
        orders = Order.query.filter_by(brand=brand).all()
        expenses = Expense.query.filter_by(brand=brand).all()
        
        # Calculate metrics
        total_revenue = sum(order.revenue for order in orders)
        total_cost = sum(order.cost for order in orders)
        total_expenses = sum(expense.amount for expense in expenses)
        total_profit = total_revenue - total_cost - total_expenses
        
        # Determine performance status
        if total_profit > 1000:  # Profitable
            status = 'winning'
            status_color = 'success'
        elif total_profit > 0:  # Break-even or slight profit
            status = 'neutral'
            status_color = 'warning'
        else:  # Loss
            status = 'losing'
            status_color = 'danger'
        
        brands_data[brand] = {
            'total_orders': len(orders),
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'total_profit': total_profit,
            'status': status,
            'status_color': status_color
        }
    
    # Get summary data for simplified home page
    total_orders = Order.query.count()
    
    # Calculate total revenue and pending payments manually since they are properties
    all_orders = Order.query.all()
    total_revenue = sum(order.total_amount for order in all_orders)
    pending_payments = sum(order.remaining_amount for order in all_orders)
    
    total_clients = Client.query.count()
    
    # Recent orders (last 5)
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Recent transfers (last 5)
    recent_transfers = MoneyTransfer.query.order_by(MoneyTransfer.created_at.desc()).limit(5).all()
    
    context = {
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_clients': total_clients,
        'pending_payments': pending_payments,
        'recent_orders': recent_orders,
        'recent_transfers': recent_transfers
    }
    
    return render_template('home.html', **context)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            session['show_welcome'] = True
            next_page = request.args.get('next')
            return redirect(next_page + '?from=login') if next_page else redirect(url_for('index') + '?from=login')
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
    if brand not in ['URBRAND', 'SURVACCI', 'AZIZ']:
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
    client_id = request.args.get('client_id', type=int)
    
    query = Order.query
    if brand_filter:
        query = query.filter_by(brand=brand_filter)
    if client_id:
        query = query.filter_by(client_id=client_id)
    
    # Auto-sort by date (newest first)
    orders = query.order_by(Order.date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('orders.html', orders=orders, brand_filter=brand_filter)

@app.route('/orders/new', methods=['GET', 'POST'])
@login_required  
def new_order():
    # Redirect to enhanced order form
    return redirect(url_for('enhanced_order'))


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
@admin_required
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

# Enhanced order management routes
@app.route('/clients', methods=['GET', 'POST'])
@login_required
def clients():
    clients = Client.query.order_by(Client.name).all()
    form = ClientForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        client = Client(
            name=form.name.data,
            phone_number=form.phone_number.data,
            email=form.email.data,
            address=form.address.data,
            notes=form.notes.data
        )
        db.session.add(client)
        db.session.commit()
        flash('Client added successfully!', 'success')
        return redirect(url_for('clients'))
    
    return render_template('clients.html', clients=clients, form=form)

@app.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    form = ClientForm(obj=client)

    if form.validate_on_submit():
        client.name = form.name.data
        client.phone_number = form.phone_number.data
        client.email = form.email.data
        client.address = form.address.data
        client.notes = form.notes.data

        try:
            db.session.commit()
            flash('Client updated successfully!', 'success')
            return redirect(url_for('clients'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating client. Please try again.', 'danger')

    return render_template('edit_client.html', form=form, client=client)

@app.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)

    try:
        # Check if client has any orders
        if client.orders:
            flash('Cannot delete client with existing orders. Delete the orders first.', 'warning')
            return redirect(url_for('clients'))

        db.session.delete(client)
        db.session.commit()
        flash('Client deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting client. Please try again.', 'danger')

    return redirect(url_for('clients'))

@app.route('/enhanced-order', methods=['GET', 'POST'])
@login_required
def enhanced_order():
    form = OrderForm()
    products = ProductType.query.all()
    
    if request.method == 'POST':
        # Handle form submission manually to process order items
        # Generate order code if not provided
        order_code = request.form.get('order_code') or Order.generate_order_code()
        
        # Handle client selection or creation
        client_id = request.form.get('client_id')
        client_id = int(client_id) if client_id and client_id != '0' else None
        client_name = request.form.get('client_name')
        
        if not client_id and client_name:
            # Create new client if name provided but no client selected
            client = Client(
                name=client_name,
                phone_number=request.form.get('phone_number'),
                email=request.form.get('email', ''),
                address=request.form.get('address', '')
            )
            db.session.add(client)
            db.session.flush()  # Get the ID
            client_id = client.id
        
        # Create order
        order = Order(
            order_code=order_code,
            client_id=client_id,
            client_name=client_name,
            phone_number=request.form.get('phone_number'),
            date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
            is_printed=bool(request.form.get('is_printed')),
            paid_amount=float(request.form.get('paid_amount', 0)),
            remaining_amount=float(request.form.get('remaining_amount', 0)),
            brand=request.form.get('brand'),
            notes=request.form.get('notes', '')
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Process order items from the order_items JSON data
        order_items_data = request.form.get('order_items_data')
        if order_items_data:
            try:
                items = json.loads(order_items_data)
                total_pieces = 0
                
                for item_data in items:
                    if item_data.get('is_custom'):
                        # Custom product with color-size matrix
                        order_item = OrderItem(
                            order_id=order.id,
                            product_type_id=None,
                            quantity=int(item_data['quantity']),
                            unit_price=float(item_data['unit_price']),
                            is_custom_product=True,
                            custom_product_name=item_data['product_name'],
                            custom_product_description=item_data.get('description', ''),
                            custom_color_size_matrix=item_data.get('color_size_matrix', '{}')
                        )
                    else:
                        # Regular product
                        order_item = OrderItem(
                            order_id=order.id,
                            product_type_id=int(item_data['product_type_id']),
                            quantity=int(item_data['quantity']),
                            unit_price=float(item_data['unit_price']),
                            color_size_breakdown=item_data.get('color_size_breakdown', '{}')
                        )
                        
                        # Update inventory for regular products
                        if item_data.get('color_size_breakdown'):
                            breakdown = json.loads(item_data['color_size_breakdown'])
                            storage_type = 'AZIZ' if order.brand == 'AZIZ' else 'SHARED'
                            
                            for color, sizes in breakdown.items():
                                for size, qty in sizes.items():
                                    if qty > 0:
                                        ColorSizeInventory.update_inventory(
                                            int(item_data['product_type_id']),
                                            storage_type,
                                            color,
                                            size,
                                            -qty  # Negative to reduce stock
                                        )
                    
                    db.session.add(order_item)
                    total_pieces += int(item_data['quantity'])
                
                # Update order total pieces
                order.total_pieces = total_pieces
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                flash(f'Error processing order items: {str(e)}', 'danger')
                db.session.rollback()
                return render_template('enhanced_order_form.html', form=form, products=products)
        
        try:
            db.session.commit()
            flash('Order created successfully!', 'success')
            return redirect(url_for('orders'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating order: {str(e)}', 'danger')
    
    return render_template('enhanced_order_form.html', form=form, products=products)

@app.route('/color-size-inventory', methods=['GET', 'POST'])
@login_required
def color_size_inventory():
    form = ColorSizeInventoryForm()
    return render_template('color_size_inventory.html', form=form)

# API Endpoints for AJAX functionality
@app.route('/api/client/<int:client_id>')
@login_required
def api_get_client(client_id):
    client = Client.query.get_or_404(client_id)
    return jsonify({
        'id': client.id,
        'name': client.name,
        'phone_number': client.phone_number,
        'email': client.email,
        'address': client.address
    })

@app.route('/api/clients', methods=['POST'])
@login_required
def api_create_client():
    data = request.get_json()
    
    try:
        client = Client(
            name=data['name'],
            phone_number=data['phone_number'],
            email=data.get('email', ''),
            address=data.get('address', '')
        )
        db.session.add(client)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'client': {
                'id': client.id,
                'name': client.name,
                'phone_number': client.phone_number
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})



@app.route('/api/inventory/save', methods=['POST'])
@login_required
def api_save_inventory():
    data = request.get_json()
    
    try:
        product_id = data['product_id']
        storage_type = data['storage_type']
        inventory_data = data['inventory']
        
        # Clear existing inventory for this product/storage combination
        ColorSizeInventory.query.filter_by(
            product_type_id=product_id,
            storage_type=storage_type
        ).delete()
        
        # Add new inventory records
        for color, sizes in inventory_data.items():
            for size, quantity in sizes.items():
                if quantity > 0:  # Only save non-zero quantities
                    inventory = ColorSizeInventory(
                        product_type_id=product_id,
                        storage_type=storage_type,
                        color=color,
                        size=size if size != 'None' else None,
                        quantity=quantity
                    )
                    db.session.add(inventory)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})



@app.route('/products')
@login_required
def products():
    form = ProductTypeForm()
    products = ProductType.query.all()
    return render_template('products.html', form=form, products=products)

@app.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    if request.method == 'POST':
        try:
            # Get form data from the modal form
            name = request.form.get('name')
            cost_price = float(request.form.get('cost_price', 0))
            selling_price = float(request.form.get('selling_price', 0))
            brand_group = request.form.get('brand_group')
            
            # Get selected colors and sizes from checkboxes
            selected_colors = request.form.getlist('available_colors')
            selected_sizes = request.form.getlist('available_sizes')
            
            # Validate required fields
            if not name or not brand_group or selling_price <= 0:
                flash('Please fill in all required fields with valid values.', 'danger')
                return redirect(url_for('products'))
            
            if not selected_colors or not selected_sizes:
                flash('Please select at least one color and one size.', 'danger')
                return redirect(url_for('products'))
            
            # Create new product
            product = ProductType(
                name=name,
                selling_price=selling_price,
                brand_group=brand_group,
                available_colors=','.join(selected_colors),
                available_sizes=','.join(selected_sizes)
            )
            db.session.add(product)
            db.session.commit()
            
            # Create initial inventory records
            storage_type = 'SHARED' if brand_group == 'SHARED' else 'AZIZ'
            inventory = Inventory(
                product_type_id=product.id,
                storage_type=storage_type,
                quantity=0
            )
            db.session.add(inventory)
            db.session.commit()
            
            flash('Product created successfully!', 'success')
            return redirect(url_for('products'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating product. Please try again.', 'danger')
            return redirect(url_for('products'))
    
    # Handle GET request - redirect to products page
    return redirect(url_for('products'))

@app.route('/products/<int:id>/edit', methods=['POST'])
@login_required
def edit_product(id):
    product = ProductType.query.get_or_404(id)
    form = ProductTypeForm()
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.selling_price = form.selling_price.data
        product.brand_group = form.brand_group.data
        product.available_colors = ','.join(form.available_colors.data) if form.available_colors.data else ''
        product.available_sizes = ','.join(form.available_sizes.data) if form.available_sizes.data else ''
        db.session.commit()
        flash('Product updated successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('products'))

@app.route('/products/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    product = ProductType.query.get_or_404(id)

    # Check if product is used in any orders
    if product.order_items:
        flash('Cannot delete product as it is used in existing orders!', 'danger')
        return redirect(url_for('products'))
    
    try:
        # Delete related inventory records first
        Inventory.query.filter_by(product_type_id=id).delete()
        
        # Delete related stock movements
        StockMovement.query.filter_by(product_type_id=id).delete()
        
        # Now delete the product
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product. Please try again.', 'danger')
    
    return redirect(url_for('products'))

@app.route('/api/products/<int:id>')
@login_required
def get_product_api(id):
    """API endpoint to get product data for editing"""
    product = ProductType.query.get_or_404(id)
    
    return jsonify({
        'success': True,
        'product': {
            'id': product.id,
            'name': product.name,
            'cost_price': product.cost_price,
            'selling_price': product.selling_price,
            'brand_group': product.brand_group,
            'available_colors': product.available_colors,
            'available_sizes': product.available_sizes
        }
    })

@app.route('/export')
@login_required
def export():
    return render_template('export.html')

@app.route('/transfers', methods=['GET', 'POST'])
@login_required
@admin_required
def transfers():
    """Money transfers tracking page - Admin only"""
    from models import MoneyTransfer
    from forms import MoneyTransferForm
    from datetime import date, datetime
    from sqlalchemy import func
    
    form = MoneyTransferForm()
    
    if form.validate_on_submit():
        transfer = MoneyTransfer(
            sender_name=form.sender_name.data,
            sender_phone=form.sender_phone.data,
            amount=form.amount.data,
            reason=form.reason.data,
            date=form.date.data,
            notes=form.notes.data
        )
        
        try:
            db.session.add(transfer)
            db.session.commit()
            flash('Money transfer recorded successfully!', 'success')
            return redirect(url_for('transfers'))
        except Exception as e:
            db.session.rollback()
            flash('Error recording transfer. Please try again.', 'danger')
    
    # Get all transfers
    transfers = MoneyTransfer.query.order_by(MoneyTransfer.date.desc()).all()
    
    # Calculate summary statistics
    today = date.today()
    today_total = db.session.query(func.sum(MoneyTransfer.amount)).filter(
        MoneyTransfer.date == today
    ).scalar() or 0
    
    month_total = db.session.query(func.sum(MoneyTransfer.amount)).filter(
        func.extract('month', MoneyTransfer.date) == today.month,
        func.extract('year', MoneyTransfer.date) == today.year
    ).scalar() or 0
    
    total_count = MoneyTransfer.query.count()
    all_time_total = db.session.query(func.sum(MoneyTransfer.amount)).scalar() or 0
    
    return render_template('transfers.html', 
                         form=form,
                         transfers=transfers,
                         today_total=today_total,
                         month_total=month_total,
                         total_count=total_count,
                         all_time_total=all_time_total)

@app.route('/transfers/<int:transfer_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_transfer(transfer_id):
    """Delete a money transfer record - Admin only"""
    from models import MoneyTransfer
    
    transfer = MoneyTransfer.query.get_or_404(transfer_id)
    
    try:
        db.session.delete(transfer)
        db.session.commit()
        flash('Transfer deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting transfer. Please try again.', 'danger')
    
    return redirect(url_for('transfers'))

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
    """Enhanced Storage Management with color/size tracking"""
    from models import ProductType
    
    # Get all products for enhanced storage
    products = ProductType.query.all()
    
    return render_template('storage.html', products=products)

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

@app.route('/api/client/<int:client_id>')
@login_required
def get_client_details(client_id):
    """Get client details for auto-filling order form"""
    try:
        client = Client.query.get_or_404(client_id)
        return jsonify({
            'success': True,
            'client': {
                'id': client.id,
                'name': client.name,
                'phone_number': client.phone_number,
                'email': client.email,
                'address': client.address
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/inventory/<int:product_id>')
@login_required
def get_inventory(product_id):
    """Get existing inventory data for a product"""
    from models import ColorSizeInventory
    
    try:
        inventory_records = ColorSizeInventory.query.filter_by(product_type_id=product_id).all()
        inventory_data = {}
        
        for record in inventory_records:
            key = f"{record.color}-{record.size}"
            inventory_data[key] = record.quantity
            
        return jsonify({
            'success': True,
            'inventory': inventory_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/inventory/<int:product_id>/<storage_type>')
@login_required  
@csrf.exempt
def get_product_inventory_by_storage(product_id, storage_type):
    """Get available inventory for a product by storage type for order form"""
    from models import ColorSizeInventory, ProductType
    
    try:
        # Get product info
        product = ProductType.query.get_or_404(product_id)
        
        # Get inventory records for this product and storage type
        inventory_records = ColorSizeInventory.query.filter_by(
            product_type_id=product_id,
            storage_type=storage_type
        ).all()
        
        # Organize by color and size
        inventory_data = {}
        for record in inventory_records:
            color = record.color
            size = record.size or 'One Size'
            
            if color not in inventory_data:
                inventory_data[color] = {}
            inventory_data[color][size] = record.quantity
            
        return jsonify({
            'success': True,
            'product_name': product.name,
            'available_colors': product.get_colors_list(),
            'available_sizes': product.get_sizes_list(),
            'inventory': inventory_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/save-inventory', methods=['POST'])
@login_required
@csrf.exempt
def save_inventory():
    """Save inventory data for color/size combinations"""
    from models import ColorSizeInventory
    from flask_wtf.csrf import validate_csrf
    from flask import request
    
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        storage_type = data.get('storage_type')
        inventory = data.get('inventory', {})
        
        # Delete existing inventory records for this product
        ColorSizeInventory.query.filter_by(product_type_id=product_id).delete()
        
        # Save new inventory data
        for key, quantity in inventory.items():
            if quantity > 0:  # Only save non-zero quantities
                color, size = key.split('-', 1)
                
                inventory_record = ColorSizeInventory(
                    product_type_id=product_id,
                    color=color,
                    size=size,
                    quantity=quantity,
                    storage_type=storage_type
                )
                db.session.add(inventory_record)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Inventory saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/expenses')
@app.route('/expenses/<brand>')
@login_required
def expenses(brand='URBRAND'):
    """Expenses management page"""
    from models import Expense
    from forms import ExpenseForm
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract
    
    if brand not in ['URBRAND', 'SURVACCI', 'AZIZ']:
        brand = 'URBRAND'
    
    # Get all expenses for selected brand
    expense_list = Expense.query.filter_by(brand=brand).order_by(Expense.date.desc()).all()
    
    # Calculate statistics
    total_expenses = sum(expense.amount for expense in expense_list)
    brand_expenses = total_expenses
    
    # Current month expenses
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_expenses = sum(
        expense.amount for expense in expense_list 
        if expense.date.month == current_month and expense.date.year == current_year
    )
    
    # Calculate average monthly expenses
    if expense_list:
        # Group expenses by month
        monthly_totals = {}
        for expense in expense_list:
            month_key = f"{expense.date.year}-{expense.date.month:02d}"
            if month_key not in monthly_totals:
                monthly_totals[month_key] = 0
            monthly_totals[month_key] += expense.amount
        
        average_monthly = sum(monthly_totals.values()) / len(monthly_totals) if monthly_totals else 0
    else:
        average_monthly = 0
    
    # Get total expenses across all brands for comparison
    all_expenses = Expense.query.all()
    total_all_brands = sum(expense.amount for expense in all_expenses)
    
    form = ExpenseForm()
    form.brand.data = brand
    
    return render_template('expenses.html', 
                         expenses=expense_list, 
                         total_expenses=total_all_brands,
                         monthly_expenses=monthly_expenses,
                         average_monthly=average_monthly,
                         brand_expenses=brand_expenses,
                         selected_brand=brand,
                         form=form)

@app.route('/expenses/new', methods=['POST'])
@login_required
def new_expense():
    """Create a new expense"""
    from models import Expense
    from datetime import datetime
    
    try:
        # Get form data directly from request
        name = request.form.get('name')
        amount = float(request.form.get('amount')) if request.form.get('amount') else 0.0
        date_str = request.form.get('date')
        brand = request.form.get('brand')
        notes = request.form.get('notes', '')
        
        # Parse date
        date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.today().date()
        
        # Validate required fields
        if not all([name, amount > 0, brand]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('expenses', brand=brand or 'URBRAND'))
        
        if brand not in ['URBRAND', 'SURVACCI', 'AZIZ']:
            flash('Invalid brand selected.', 'danger')
            return redirect(url_for('expenses', brand='URBRAND'))
        
        # Create expense
        expense = Expense(
            name=name,
            amount=amount,
            date=date,
            brand=brand,
            notes=notes,
            created_by=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('expenses', brand=brand))
        
    except Exception as e:
        db.session.rollback()
        flash('Error creating expense. Please try again.', 'danger')
        return redirect(url_for('expenses', brand=request.form.get('brand', 'URBRAND')))
    
    return redirect(url_for('expenses'))

@app.route('/expenses/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_expense(id):
    """Delete an expense - Admin only"""
    from models import Expense
    
    expense = Expense.query.get_or_404(id)
    brand = expense.brand
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('expenses', brand=brand))

@app.route('/expenses/export/<brand>')
@login_required
def export_expenses_csv(brand):
    """Export expenses to CSV"""
    from models import Expense
    import csv
    from io import StringIO
    
    expense_list = Expense.query.filter_by(brand=brand).order_by(Expense.date.desc()).all()
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Date', 'Expense Name', 'Amount (EGP)', 'Notes', 'Created At'])
    
    for expense in expense_list:
        writer.writerow([
            expense.date.strftime('%Y-%m-%d'),
            expense.name,
            f"{expense.amount:.2f}",
            expense.notes,
            expense.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    output.seek(0)
    filename = f'{brand}_expenses_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

@app.route('/api/product/<int:product_id>/colors')
@login_required
def get_product_colors(product_id):
    """API endpoint to get available colors for a product"""
    from models import ProductType
    
    product = ProductType.query.get_or_404(product_id)
    colors = [color.strip() for color in product.available_colors.split(',') if color.strip()]
    
    return jsonify({'colors': colors})

@app.route('/api/product/<int:product_id>/sizes')
@login_required
def get_product_sizes(product_id):
    """API endpoint to get available sizes for a product"""
    from models import ProductType
    
    product = ProductType.query.get_or_404(product_id)
    sizes = [size.strip() for size in product.available_sizes.split(',') if size.strip()]
    
    return jsonify({'sizes': sizes})

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page to update username and password"""
    form = UserProfileForm(current_user.username, current_user.email)
    
    if form.validate_on_submit():
        # Verify current password
        if not check_password_hash(current_user.password_hash, form.current_password.data):
            flash('Current password is incorrect', 'danger')
            return render_template('profile.html', form=form)
        
        # Update username and email
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        # Update password if provided
        if form.new_password.data:
            current_user.password_hash = generate_password_hash(form.new_password.data)
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'danger')
    
    # Pre-populate form with current user data
    form.username.data = current_user.username
    form.email.data = current_user.email
    
    return render_template('profile.html', form=form)


# User Management Routes (Admin Only)

@app.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def user_management():
    """User management page - Admin only"""
    users = User.query.all()

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')

        # Validate input
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('user_management'))

        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('user_management'))

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('user_management'))

        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash(f'User "{username}" created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error creating user. Please try again.', 'danger')

        return redirect(url_for('user_management'))

    return render_template('user_management.html', users=users)


@app.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user - Admin only"""
    user = User.query.get_or_404(user_id)

    # Prevent editing own admin status
    if user.id == current_user.id:
        flash('You cannot change your own role', 'warning')
        return redirect(url_for('user_management'))

    role = request.form.get('role', 'user')
    user.role = role

    try:
        db.session.commit()
        flash(f'User "{user.username}" updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating user. Please try again.', 'danger')

    return redirect(url_for('user_management'))


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user - Admin only"""
    user = User.query.get_or_404(user_id)

    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('user_management'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{user.username}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting user. Please try again.', 'danger')

    return redirect(url_for('user_management'))


@app.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    """Reset user password - Admin only"""
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')

    if not new_password:
        flash('Password is required', 'danger')
        return redirect(url_for('user_management'))

    user.password_hash = generate_password_hash(new_password)

    try:
        db.session.commit()
        flash(f'Password reset for "{user.username}"', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error resetting password. Please try again.', 'danger')

    return redirect(url_for('user_management'))


# Worker Management Routes

@app.route('/workers')
@login_required
def workers():
    """Workers management page"""
    workers = Worker.query.filter_by(is_active=True).all()
    
    # Calculate monthly stats for each worker
    today = datetime.utcnow().date()
    start_of_month = today.replace(day=1)
    
    worker_stats = []
    for worker in workers:
        attendances = WorkerAttendance.query.filter(
            WorkerAttendance.worker_id == worker.id,
            WorkerAttendance.date >= start_of_month,
            WorkerAttendance.date <= today
        ).all()
        
        total_days = len([a for a in attendances if a.present])
        total_salary = sum(a.calculate_daily_pay() for a in attendances)
        total_overtime = sum(a.overtime_hours for a in attendances)
        
        worker_stats.append({
            'worker': worker,
            'days_worked': total_days,
            'total_salary': total_salary,
            'total_overtime': total_overtime
        })
    
    return render_template('workers.html', worker_stats=worker_stats)


@app.route('/workers/new', methods=['GET', 'POST'])
@login_required
def new_worker():
    """Add a new worker"""
    from models import Worker
    form = WorkerForm()
    
    if form.validate_on_submit():
        try:
            # Create worker
            worker = Worker(
                name=form.name.data,
                phone_number=form.phone_number.data,
                daily_salary=form.daily_salary.data,
                overtime_rate=form.overtime_rate.data,
                department=form.department.data,
                assigned_brand=form.assigned_brand.data,
                piece_rate_enabled=form.piece_rate_enabled.data,
                tier1_threshold=form.tier1_threshold.data,
                tier1_rate=form.tier1_rate.data,
                tier2_threshold=form.tier2_threshold.data,
                tier2_rate=form.tier2_rate.data,
                tier3_threshold=form.tier3_threshold.data,
                tier3_rate=form.tier3_rate.data,
                tier4_rate=form.tier4_rate.data,
                position=form.position.data,
                hire_date=form.hire_date.data,
                is_active=form.is_active.data,
                notes=form.notes.data
            )
            
            db.session.add(worker)
            db.session.commit()
            
            flash(f'Worker {form.name.data} added successfully!', 'success')
            return redirect(url_for('workers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding worker: {str(e)}', 'danger')
    
    return render_template('worker_form.html', form=form, title='Add New Worker')


@app.route('/workers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_worker(id):
    """Edit a worker"""
    worker = Worker.query.get_or_404(id)
    form = WorkerForm(obj=worker)
    
    if form.validate_on_submit():
        worker.name = form.name.data
        worker.phone_number = form.phone_number.data
        worker.daily_salary = form.daily_salary.data
        worker.overtime_rate = form.overtime_rate.data
        worker.piece_rate_enabled = form.piece_rate_enabled.data
        worker.base_piece_rate = form.base_piece_rate.data
        worker.bonus_threshold = form.bonus_threshold.data
        worker.bonus_piece_rate = form.bonus_piece_rate.data
        worker.position = form.position.data
        worker.hire_date = form.hire_date.data
        worker.is_active = form.is_active.data
        worker.notes = form.notes.data
        
        try:
            db.session.commit()
            flash('Worker updated successfully', 'success')
            return redirect(url_for('workers'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating worker', 'danger')
    
    return render_template('worker_form.html', form=form, worker=worker, title="Edit Worker")


@app.route('/workers/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_worker(id):
    """Deactivate a worker - Admin only"""
    worker = Worker.query.get_or_404(id)
    worker.is_active = False
    
    try:
        db.session.commit()
        flash('Worker deactivated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deactivating worker', 'danger')
    
    return redirect(url_for('workers'))


@app.route('/attendance')
@login_required
def attendance():
    """Attendance tracking page"""
    filter_form = AttendanceFilterForm()
    
    # Get filter parameters
    worker_id_str = request.args.get('worker_id', '0')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = WorkerAttendance.query.join(Worker)
    
    # Handle worker filter (0 means all workers)
    try:
        worker_id = int(worker_id_str) if worker_id_str and worker_id_str != '0' else None
        if worker_id:
            query = query.filter(WorkerAttendance.worker_id == worker_id)
    except (ValueError, TypeError):
        worker_id = None
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(WorkerAttendance.date >= date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(WorkerAttendance.date <= date_to)
        except ValueError:
            pass
    
    # Default to current month if no filters
    if not any([worker_id, date_from, date_to]):
        today = datetime.utcnow().date()
        start_of_month = today.replace(day=1)
        query = query.filter(WorkerAttendance.date >= start_of_month)
    
    attendances = query.order_by(WorkerAttendance.date.desc()).all()
    
    return render_template('attendance.html', 
                         attendances=attendances, 
                         filter_form=filter_form)


@app.route('/attendance/new', methods=['GET', 'POST'])
@login_required
def new_attendance():
    """Record new attendance"""
    form = AttendanceForm()
    
    if form.validate_on_submit():
        # Check if attendance already exists for this worker on this date
        existing = WorkerAttendance.query.filter_by(
            worker_id=form.worker_id.data,
            date=form.date.data
        ).first()
        
        if existing:
            flash('Attendance already recorded for this worker on this date', 'warning')
            return render_template('attendance_form.html', form=form, title="Record Attendance")
        
        attendance = WorkerAttendance(
            worker_id=form.worker_id.data,
            date=form.date.data,
            present=form.present.data,
            check_in_time=form.check_in_time.data,
            check_out_time=form.check_out_time.data,
            overtime_hours=form.overtime_hours.data,
            pieces_completed=form.pieces_completed.data,
            deductions=form.deductions.data,
            deduction_reason=form.deduction_reason.data,
            bonus=form.bonus.data,
            bonus_reason=form.bonus_reason.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        try:
            db.session.add(attendance)
            db.session.commit()
            flash('Attendance recorded successfully', 'success')
            return redirect(url_for('attendance'))
        except Exception as e:
            db.session.rollback()
            flash('Error recording attendance', 'danger')
    
    return render_template('attendance_form.html', form=form, title="Record Attendance")


@app.route('/attendance/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_attendance(id):
    """Edit attendance record"""
    attendance = WorkerAttendance.query.get_or_404(id)
    form = AttendanceForm(obj=attendance)
    
    if form.validate_on_submit():
        attendance.worker_id = form.worker_id.data
        attendance.date = form.date.data
        attendance.present = form.present.data
        attendance.check_in_time = form.check_in_time.data
        attendance.check_out_time = form.check_out_time.data
        attendance.overtime_hours = form.overtime_hours.data
        attendance.pieces_completed = form.pieces_completed.data
        attendance.deductions = form.deductions.data
        attendance.deduction_reason = form.deduction_reason.data
        attendance.bonus = form.bonus.data
        attendance.bonus_reason = form.bonus_reason.data
        attendance.notes = form.notes.data
        
        try:
            db.session.commit()
            flash('Attendance updated successfully', 'success')
            return redirect(url_for('attendance'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating attendance', 'danger')
    
    return render_template('attendance_form.html', form=form, attendance=attendance, title="Edit Attendance")


@app.route('/attendance/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_attendance(id):
    """Delete attendance record - Admin only"""
    attendance = WorkerAttendance.query.get_or_404(id)
    
    try:
        db.session.delete(attendance)
        db.session.commit()
        flash('Attendance record deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting attendance record', 'danger')
    
    return redirect(url_for('attendance'))


@app.route('/workers/<int:id>/report')
@login_required
def worker_report(id):
    """Generate detailed report for a specific worker"""
    worker = Worker.query.get_or_404(id)
    
    # Get date range (default to current month)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if not date_from or not date_to:
        today = datetime.utcnow().date()
        date_from = today.replace(day=1)
        date_to = today
    else:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            today = datetime.utcnow().date()
            date_from = today.replace(day=1)
            date_to = today
    
    # Get attendance records
    attendances = WorkerAttendance.query.filter(
        WorkerAttendance.worker_id == worker.id,
        WorkerAttendance.date >= date_from,
        WorkerAttendance.date <= date_to
    ).order_by(WorkerAttendance.date).all()
    
    # Calculate statistics
    total_days = len([a for a in attendances if a.present])
    total_salary = sum(a.calculate_daily_pay() for a in attendances)
    total_overtime = sum(a.overtime_hours for a in attendances)
    total_deductions = sum(a.deductions for a in attendances)
    total_bonuses = sum(a.bonus for a in attendances)
    
    stats = {
        'total_days': total_days,
        'total_salary': total_salary,
        'total_overtime': total_overtime,
        'total_deductions': total_deductions,
        'total_bonuses': total_bonuses,
        'net_salary': total_salary
    }
    
    return render_template('worker_report.html', 
                         worker=worker, 
                         attendances=attendances,
                         stats=stats,
                         date_from=date_from,
                         date_to=date_to)


