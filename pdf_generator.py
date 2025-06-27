import os
import tempfile
from datetime import datetime
from fpdf import FPDF
from typing import Any, Dict, List, Optional

from models import Order

class InvoicePDF(FPDF):
    """Custom PDF class for generating invoices."""
    
    def header(self):
        """Create the header section of the PDF."""
        # Logo - We'll use text since we can't include image files
        self.set_font('Arial', 'B', 20)
        self.cell(0, 10, 'SmartCartPro', 0, 1, 'L')
        
        # Company info
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'Your trusted grocery & pharmacy partner', 0, 1, 'L')
        self.cell(0, 5, 'contact@smartcartpro.com | +1-800-SMART-CART', 0, 1, 'L')
        
        # Line break
        self.ln(10)
    
    def footer(self):
        """Create the footer section of the PDF."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        self.cell(0, 10, 'Thank you for shopping with SmartCartPro!', 0, 0, 'R')
    
    def invoice_title(self, invoice_no: str, date: str):
        """Add the invoice title."""
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'INVOICE', 0, 1, 'C')
        self.ln(5)
        
        # Invoice details
        self.set_font('Arial', 'B', 11)
        self.cell(40, 7, 'Invoice No:', 0, 0)
        self.set_font('Arial', '', 11)
        self.cell(100, 7, invoice_no, 0, 0)
        self.set_font('Arial', 'B', 11)
        self.cell(25, 7, 'Date:', 0, 0)
        self.set_font('Arial', '', 11)
        self.cell(25, 7, date, 0, 1)
        self.ln(5)
    
    def customer_info(self, customer: Dict[str, str], address: str):
        """Add customer information."""
        self.set_font('Arial', 'B', 11)
        self.cell(40, 7, 'Bill To:', 0, 1)
        self.set_font('Arial', '', 11)
        self.cell(0, 7, customer['name'], 0, 1)
        self.cell(0, 7, customer['email'], 0, 1)
        
        # Delivery address
        self.set_font('Arial', 'B', 11)
        self.cell(40, 7, 'Delivery Address:', 0, 1)
        self.set_font('Arial', '', 11)
        
        # Handle multiline address
        for line in address.split('\n'):
            self.cell(0, 7, line, 0, 1)
        
        self.ln(5)
    
    def invoice_items_header(self):
        """Add the table header for invoice items."""
        self.set_fill_color(240, 240, 240)
        self.set_font('Arial', 'B', 10)
        
        # Header
        self.cell(10, 10, 'No.', 1, 0, 'C', True)
        self.cell(80, 10, 'Description', 1, 0, 'C', True)
        self.cell(25, 10, 'Quantity', 1, 0, 'C', True)
        self.cell(35, 10, 'Unit Price', 1, 0, 'C', True)
        self.cell(40, 10, 'Amount', 1, 1, 'C', True)
    
    def invoice_items(self, items: List[Dict[str, Any]]):
        """Add the invoice items to the table."""
        self.set_font('Arial', '', 10)
        
        # Items
        for i, item in enumerate(items, 1):
            self.cell(10, 7, str(i), 1, 0, 'C')
            self.cell(80, 7, item['name'], 1, 0, 'L')
            self.cell(25, 7, str(item['quantity']), 1, 0, 'C')
            self.cell(35, 7, f"${item['unit_price']:.2f}", 1, 0, 'R')
            self.cell(40, 7, f"${item['amount']:.2f}", 1, 1, 'R')
    
    def invoice_totals(self, subtotal: float, discount: float = 0, shipping: float = 0, tax: float = 0):
        """Add the invoice totals section."""
        self.set_font('Arial', '', 10)
        
        # Right align totals
        self.cell(115, 7, '', 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(35, 7, 'Subtotal:', 1, 0, 'R')
        self.set_font('Arial', '', 10)
        self.cell(40, 7, f"${subtotal:.2f}", 1, 1, 'R')
        
        if discount > 0:
            self.cell(115, 7, '', 0, 0)
            self.set_font('Arial', 'B', 10)
            self.cell(35, 7, 'Discount:', 1, 0, 'R')
            self.set_font('Arial', '', 10)
            self.cell(40, 7, f"-${discount:.2f}", 1, 1, 'R')
        
        if shipping > 0:
            self.cell(115, 7, '', 0, 0)
            self.set_font('Arial', 'B', 10)
            self.cell(35, 7, 'Shipping:', 1, 0, 'R')
            self.set_font('Arial', '', 10)
            self.cell(40, 7, f"${shipping:.2f}", 1, 1, 'R')
        
        if tax > 0:
            self.cell(115, 7, '', 0, 0)
            self.set_font('Arial', 'B', 10)
            self.cell(35, 7, 'Tax:', 1, 0, 'R')
            self.set_font('Arial', '', 10)
            self.cell(40, 7, f"${tax:.2f}", 1, 1, 'R')
        
        # Total
        total = subtotal - discount + shipping + tax
        self.cell(115, 7, '', 0, 0)
        self.set_font('Arial', 'B', 10)
        self.cell(35, 7, 'Total:', 1, 0, 'R', True)
        self.cell(40, 7, f"${total:.2f}", 1, 1, 'R', True)
    
    def payment_info(self):
        """Add payment information."""
        self.ln(10)
        self.set_font('Arial', 'B', 11)
        self.cell(0, 7, 'Payment Information:', 0, 1)
        self.set_font('Arial', '', 10)
        self.cell(0, 7, 'Payment received online.', 0, 1)
        self.cell(0, 7, 'Thank you for your purchase!', 0, 1)
    
    def terms_conditions(self):
        """Add terms and conditions."""
        self.ln(10)
        self.set_font('Arial', 'B', 11)
        self.cell(0, 7, 'Terms & Conditions:', 0, 1)
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, 'All items are non-returnable for hygiene and safety reasons. ' +
                       'For damaged or incorrect items, please contact customer support within 24 hours of delivery. ' +
                       'Medicines must be used as prescribed by your healthcare provider.')

def generate_invoice_pdf(order: Order) -> str:
    """
    Generate a PDF invoice for an order.
    
    Args:
        order: The Order object to generate an invoice for
    
    Returns:
        The path to the generated PDF file
    """
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix='.pdf')
    os.close(fd)
    
    # Create PDF instance
    pdf = InvoicePDF()
    pdf.add_page()
    
    # Invoice title and info
    invoice_date = order.created_at.strftime('%Y-%m-%d')
    invoice_no = f"INV-{order.id}"
    pdf.invoice_title(invoice_no, invoice_date)
    
    # Customer info
    customer = {
        'name': order.customer.username,
        'email': order.customer.email
    }
    pdf.customer_info(customer, order.delivery_address)
    
    # Invoice items
    pdf.invoice_items_header()
    
    items = []
    for item in order.items:
        items.append({
            'name': item.product.name,
            'quantity': item.quantity,
            'unit_price': item.price,
            'amount': item.quantity * item.price
        })
    
    pdf.invoice_items(items)
    
    # Calculate subtotal
    subtotal = sum(item['amount'] for item in items)
    
    # Add totals (no discount, shipping, or tax for simplicity)
    pdf.invoice_totals(subtotal)
    
    # Add payment info and terms
    pdf.payment_info()
    pdf.terms_conditions()
    
    # Output PDF to file
    pdf.output(path)
    
    return path
