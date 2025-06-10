from flask import render_template, redirect, url_for, flash, request, jsonify, make_response, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from models import User, Order, ProductType, Inventory, StockMovement, Worker, WorkerAttendance
from forms import LoginForm, OrderForm, ProductTypeForm, UserProfileForm, WorkerForm, AttendanceForm, AttendanceFilterForm
from utils import generate_invoice_pdf, export_data_csv
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import json

@app.route('/')
@login_required
def index():
    """Home page with brand overview and performance indicators"""
    # Clear welcome flag after first visit
    show_welcome = session.pop('show_welcome', False)
    from models import Order, Expense
    
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
    
    return render_template('home.html', brands_data=brands_data)

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
    if request.method == 'POST':
        try:
            # Get form data
            client_name = request.form.get('client_name')
            phone_number = request.form.get('phone_number')
            date_str = request.form.get('date')
            product_type_id = int(request.form.get('product_type_id')) if request.form.get('product_type_id') else None
            total_pieces = int(request.form.get('total_pieces')) if request.form.get('total_pieces') else 0
            pieces_per_color = int(request.form.get('pieces_per_color')) if request.form.get('pieces_per_color') else 0
            is_printed = bool(request.form.get('is_printed'))
            paid_amount = float(request.form.get('paid_amount')) if request.form.get('paid_amount') else 0.0
            remaining_amount = float(request.form.get('remaining_amount')) if request.form.get('remaining_amount') else 0.0
            brand = request.form.get('brand')
            
            # Get selected colors and sizes from the hidden multi-select fields
            selected_colors = request.form.getlist('selected_colors')
            selected_sizes = request.form.getlist('selected_sizes')
            
            # Parse date
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.today().date()
            
            # Validate required fields
            if not all([client_name, phone_number, product_type_id, total_pieces, brand]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('order_form.html', form=form, title='New Order')
            
            if not selected_colors or not selected_sizes:
                flash('Please select at least one color and one size.', 'danger')
                return render_template('order_form.html', form=form, title='New Order')
            
            # Check stock availability before creating order
            available_stock = Inventory.get_available_stock(product_type_id, brand)
            
            if available_stock < total_pieces:
                flash(f'Insufficient stock! Available: {available_stock}, Required: {total_pieces}', 'danger')
                return render_template('order_form.html', form=form, title='New Order')
            
            # Create the order
            order = Order(
                client_name=client_name,
                phone_number=phone_number,
                date=date,
                product_type_id=product_type_id,
                total_pieces=total_pieces,
                selected_colors=','.join(selected_colors),
                selected_sizes=','.join(selected_sizes),
                pieces_per_color=pieces_per_color,
                is_printed=is_printed,
                paid_amount=paid_amount,
                remaining_amount=remaining_amount,
                brand=brand
            )
            db.session.add(order)
            db.session.flush()  # Get the order ID
            
            # Update inventory
            Inventory.update_stock(product_type_id, brand, total_pieces)
            
            # Record stock movement
            stock_movement = StockMovement(
                product_type_id=product_type_id,
                storage_type='SHARED' if brand in ['URBRAND', 'SURVACCI'] else 'AZIZ',
                movement_type='ORDER',
                quantity=-total_pieces,
                order_id=order.id,
                notes=f'Order #{order.id} for {client_name}',
                created_by=current_user.id
            )
            db.session.add(stock_movement)
            db.session.commit()
            
            flash('Order created successfully!', 'success')
            return redirect(url_for('orders'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating order. Please try again.', 'danger')
            return render_template('order_form.html', form=form, title='New Order')
        
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
            if not name or not brand_group or cost_price <= 0 or selling_price <= 0:
                flash('Please fill in all required fields with valid values.', 'danger')
                return redirect(url_for('products'))
            
            if selling_price <= cost_price:
                flash('Selling price must be higher than cost price.', 'danger')
                return redirect(url_for('products'))
            
            if not selected_colors or not selected_sizes:
                flash('Please select at least one color and one size.', 'danger')
                return redirect(url_for('products'))
            
            # Create new product
            product = ProductType(
                name=name,
                cost_price=cost_price,
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
        product.cost_price = form.cost_price.data
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
def delete_product(id):
    product = ProductType.query.get_or_404(id)
    
    # Check if product is used in any orders
    if product.orders:
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
    
    # Get products filtered by brand group
    shared_products = ProductType.query.filter_by(brand_group='SHARED').all()
    aziz_products = ProductType.query.filter_by(brand_group='AZIZ').all()
    
    # Get inventory data for shared storage products
    shared_inventory = {}
    for product in shared_products:
        shared_stock = Inventory.query.filter_by(
            product_type_id=product.id,
            storage_type='SHARED'
        ).first()
        shared_inventory[product.id] = shared_stock.quantity if shared_stock else 0
    
    # Get inventory data for AZIZ storage products
    aziz_inventory = {}
    for product in aziz_products:
        aziz_stock = Inventory.query.filter_by(
            product_type_id=product.id,
            storage_type='AZIZ'
        ).first()
        aziz_inventory[product.id] = aziz_stock.quantity if aziz_stock else 0
    
    return render_template('storage.html',
                         shared_products=shared_products,
                         aziz_products=aziz_products,
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

@app.route('/expenses')
@app.route('/expenses/<brand>')
@login_required
def expenses(brand='URBRAND'):
    """Expenses management page"""
    from models import Expense
    from forms import ExpenseForm
    
    if brand not in ['URBRAND', 'SURVACCI', 'AZIZ']:
        brand = 'URBRAND'
    
    expense_list = Expense.query.filter_by(brand=brand).order_by(Expense.date.desc()).all()
    total_expenses = sum(expense.amount for expense in expense_list)
    
    form = ExpenseForm()
    form.brand.data = brand
    
    return render_template('expenses.html', 
                         expenses=expense_list, 
                         total_expenses=total_expenses,
                         selected_brand=brand,
                         form=form)

@app.route('/expenses/new', methods=['POST'])
@login_required
def new_expense():
    """Create a new expense"""
    from models import Expense
    from forms import ExpenseForm
    
    form = ExpenseForm()
    if form.validate_on_submit():
        expense = Expense(
            name=form.name.data,
            amount=form.amount.data,
            date=form.date.data,
            brand=form.brand.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('expenses', brand=form.brand.data))
    
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('expenses'))

@app.route('/expenses/<int:id>/delete', methods=['POST'])
@login_required
def delete_expense(id):
    """Delete an expense"""
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
    form = WorkerForm()
    
    if form.validate_on_submit():
        worker = Worker(
            name=form.name.data,
            phone_number=form.phone_number.data,
            daily_salary=form.daily_salary.data,
            overtime_rate=form.overtime_rate.data,
            piece_rate_enabled=form.piece_rate_enabled.data,
            base_piece_rate=form.base_piece_rate.data,
            bonus_threshold=form.bonus_threshold.data,
            bonus_piece_rate=form.bonus_piece_rate.data,
            position=form.position.data,
            hire_date=form.hire_date.data,
            is_active=form.is_active.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        try:
            db.session.add(worker)
            db.session.commit()
            flash('Worker added successfully', 'success')
            return redirect(url_for('workers'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding worker', 'danger')
    
    return render_template('worker_form.html', form=form, title="Add New Worker")


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
def delete_worker(id):
    """Deactivate a worker"""
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
def delete_attendance(id):
    """Delete attendance record"""
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
