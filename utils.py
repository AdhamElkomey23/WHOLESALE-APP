from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
import csv
from io import StringIO
from models import Order, ProductType
from datetime import datetime

def generate_invoice_pdf(order):
    """Generate PDF invoice for an order"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    # Build the document
    story = []
    
    # Title
    title = Paragraph(f"{order.brand} - Invoice #{order.id:04d}", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Client information
    client_info = [
        ['Invoice Date:', datetime.now().strftime('%Y-%m-%d')],
        ['Order Date:', order.date.strftime('%Y-%m-%d')],
        ['Client Name:', order.client_name],
        ['Phone Number:', order.phone_number],
        ['Brand:', order.brand]
    ]
    
    client_table = Table(client_info, colWidths=[2*inch, 3*inch])
    client_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 30))
    
    # Order details
    order_data = [
        ['Description', 'Quantity', 'Unit Price (EGP)', 'Total (EGP)'],
        [
            order.product_type_obj.name if order.product_type_obj else 'Unknown Product',
            str(order.total_pieces),
            f"{order.product_type_obj.selling_price:.2f}" if order.product_type_obj else "0.00",
            f"{order.total_amount:.2f}"
        ]
    ]
    
    order_table = Table(order_data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 1.5*inch])
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(order_table)
    story.append(Spacer(1, 20))
    
    # Additional details
    details_data = [
        ['Number of Colors:', str(order.number_of_colors)],
        ['Pieces per Color:', str(order.pieces_per_color)],
        ['Printed:', 'Yes' if order.is_printed else 'No'],
        ['', ''],
        ['Total Amount:', f"{order.total_amount:.2f} EGP"],
        ['Paid Amount:', f"{order.paid_amount:.2f} EGP"],
        ['Remaining Amount:', f"{order.remaining_amount:.2f} EGP"]
    ]
    
    details_table = Table(details_data, colWidths=[2*inch, 2*inch])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -3), (-1, -1), 12),
    ]))
    story.append(details_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def export_data_csv(brand_filter=''):
    """Export order data to CSV format"""
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    headers = [
        'Order ID', 'Date', 'Client Name', 'Phone', 'Brand', 'Product Type',
        'Total Pieces', 'Colors', 'Pieces/Color', 'Printed', 
        'Cost Price', 'Selling Price', 'Total Revenue', 'Total Cost', 'Profit',
        'Paid Amount', 'Remaining Amount'
    ]
    writer.writerow(headers)
    
    # Get orders
    query = Order.query
    if brand_filter:
        query = query.filter_by(brand=brand_filter)
    
    orders = query.order_by(Order.date.desc()).all()
    
    # Write data
    for order in orders:
        product_name = order.product_type_obj.name if order.product_type_obj else 'Unknown'
        cost_price = order.product_type_obj.cost_price if order.product_type_obj else 0
        selling_price = order.product_type_obj.selling_price if order.product_type_obj else 0
        
        row = [
            order.id,
            order.date.strftime('%Y-%m-%d'),
            order.client_name,
            order.phone_number,
            order.brand,
            product_name,
            order.total_pieces,
            order.number_of_colors,
            order.pieces_per_color,
            'Yes' if order.is_printed else 'No',
            f"{cost_price:.2f}",
            f"{selling_price:.2f}",
            f"{order.revenue:.2f}",
            f"{order.cost:.2f}",
            f"{order.profit:.2f}",
            f"{order.paid_amount:.2f}",
            f"{order.remaining_amount:.2f}"
        ]
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue()
