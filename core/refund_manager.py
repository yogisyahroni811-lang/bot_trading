"""
Refund Policy Management System for Sentinel-X

Handles order tracking, refund eligibility, and refund processing.

Refund Rules:
- TRIAL: No refunds (free)
- PRO/ENTERPRISE: 
  - 30 days from purchase date if NOT activated
  - 90% refund (10% processing fee)
  - No refunds after activation (hardware-locked)
- Requires: Order ID, License Key, Reason
"""

import os
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from core.license_manager import LicenseManager
from core.encryption import get_encryptor

@dataclass
class Order:
    """Represents a license purchase order."""
    order_id: str
    license_key: str
    tier: str
    customer_email: str
    amount_paid: float
    currency: str
    payment_method: str
    purchased_at: int
    refunded_at: Optional[int]
    status: str

class RefundManager:
    """Manages orders, refunds, and financial records."""
    
    ORDERS_FILE = "config/orders.enc"
    REFUND_WINDOW_DAYS = 30
    PROCESSING_FEE_PERCENT = 10.0
    MIN_REFUNDABLE_AMOUNT = 10.0
    
    # Status constants
    STATUS_PENDING = "pending"           # Order created, not paid
    STATUS_PAID = "paid"               # Payment confirmed
    STATUS_ACTIVATED = "activated"     # License activated on device
    STATUS_REFUNDED = "refunded"       # Refund processed
    STATUS_EXPIRED = "expired"         # Refund window expired
    
    def __init__(self):
        self.license_manager = LicenseManager()
        self.encryptor = get_encryptor()
        
    def create_order(self, license_key: str, tier: str, customer_email: str, 
                     amount_paid: float, currency: str = "USD", 
                     payment_method: str = "unknown") -> Order:
        """Create a new purchase order."""
        
        # Validate tier
        if tier not in self.license_manager.TIERS:
            raise ValueError(f"Invalid tier: {tier}")
        
        # Validate amount
        if amount_paid <= 0:
            raise ValueError("Amount must be positive")
        
        order = Order(
            order_id=str(uuid.uuid4()).replace("-", "").upper()[:12],
            license_key=license_key,
            tier=tier,
            customer_email=customer_email,
            amount_paid=amount_paid,
            currency=currency.upper(),
            payment_method=payment_method,
            purchased_at=int(time.time()),
            refunded_at=None,
            status=self.STATUS_PAID
        )
        
        # Save order
        self._save_order(order)
        
        return order
    
    def check_refund_eligibility(self, order_id: str) -> Tuple[bool, str]:
        """
        Check if an order is eligible for refund.
        
        Returns:
            (is_eligible: bool, reason: str)
        """
        order = self._load_order(order_id)
        
        if not order:
            return False, "Order not found"
        
        # Check if already refunded
        if order.status == self.STATUS_REFUNDED:
            return False, "Order already refunded"
        
        # Check if license activated
        license_data = self.license_manager.load_license()
        if license_data:
            is_valid = self.license_manager.validate_license(license_data)[0]
            if is_valid:
                return False, "License activated - hardware locked, no refunds allowed"
        
        # Check refund window
        purchased_time = datetime.fromtimestamp(order.purchased_at)
        now = datetime.now()
        days_since_purchase = (now - purchased_time).days
        
        if days_since_purchase > self.REFUND_WINDOW_DAYS:
            return False, f"Refund window expired. {days_since_purchase} days since purchase (max {self.REFUND_WINDOW_DAYS} days)"
        
        # Check minimum refund amount
        refund_amount = self._calculate_refund_amount(order.amount_paid)
        if refund_amount < self.MIN_REFUNDABLE_AMOUNT:
            return False, f"Refund amount (${refund_amount:.2f}) below minimum (${self.MIN_REFUNDABLE_AMOUNT:.2f})"
        
        return True, "Eligible for refund"
    
    def process_refund(self, order_id: str, reason: str) -> Dict:
        """
        Process a refund for an eligible order.
        
        Returns:
            Dictionary with refund details
        """
        result = {
            "success": False,
            "order_id": order_id,
            "refund_amount": 0.0,
            "processing_fee": 0.0,
            "currency": "USD",
            "message": "",
            "refund_date": None
        }
        
        # Check eligibility
        is_eligible, eligibility_reason = self.check_refund_eligibility(order_id)
        
        if not is_eligible:
            result["message"] = f"Refund denied: {eligibility_reason}"
            return result
        
        order = self._load_order(order_id)
        
        if not order:
            result["message"] = "Order not found"
            return result
        
        # Calculate amounts
        refund_amount = self._calculate_refund_amount(order.amount_paid)
        processing_fee = self._calculate_processing_fee(order.amount_paid)
        refund_date = datetime.now()
        
        # Update order
        order.status = self.STATUS_REFUNDED
        order.refunded_at = int(refund_date.timestamp())
        
        # Save updated order
        if self._save_order(order):
            result.update({
                "success": True,
                "refund_amount": refund_amount,
                "processing_fee": processing_fee,
                "currency": order.currency,
                "message": f"Refund processed successfully",
                "refund_date": refund_date.isoformat()
            })
        else:
            result["message"] = "Failed to save refund status"
        
        return result
    
    def request_refund(self, order_id: str, reason: str, 
                       customer_email: str) -> Dict:
        """
        Submit a refund request for approval.
        
        Returns:
            Refund request with pending status
        """
        # Verify order belongs to customer
        order = self._load_order(order_id)
        if not order:
            return {
                "success": False,
                "message": "Order not found"
            }
        
        if order.customer_email != customer_email:
            return {
                "success": False,
                "message": "Email does not match order records"
            }
        
        # Check eligibility
        is_eligible, eligibility_reason = self.check_refund_eligibility(order_id)
        
        if not is_eligible:
            return {
                "success": False,
                "message": eligibility_reason
            }
        
        # Generate refund request record
        refund_request = {
            "refund_request_id": str(uuid.uuid4()),
            "order_id": order_id,
            "customer_email": customer_email,
            "reason": reason,
            "requested_at": datetime.now().isoformat(),
            "status": "PENDING_REVIEW",
            "refund_amount": self._calculate_refund_amount(order.amount_paid),
            "processing_fee": self._calculate_processing_fee(order.amount_paid),
            "currency": order.currency,
            "notes": ""
        }
        
        # Save refund request
        self._save_refund_request(refund_request)
        
        return {
            "success": True,
            "message": "Refund request submitted successfully. We'll review within 48 hours.",
            "refund_request_id": refund_request["refund_request_id"],
            "refund_amount": refund_request["refund_amount"],
            "processing_fee": refund_request["processing_fee"],
            "currency": order.currency
        }
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        return self._load_order(order_id)
    
    def get_orders_by_email(self, customer_email: str, 
                           limit: int = 100) -> list:
        """Get all orders for a customer email."""
        all_orders = self._load_all_orders()
        return [o for o in all_orders if o.customer_email == customer_email][:limit]
    
    def _save_order(self, order: Order) -> bool:
        """Save order to encrypted storage."""
        try:
            os.makedirs("config", exist_ok=True)
            
            # Convert to dict
            order_dict = {
                "order_id": order.order_id,
                "license_key": order.license_key,
                "tier": order.tier,
                "customer_email": order.customer_email,
                "amount_paid": order.amount_paid,
                "currency": order.currency,
                "payment_method": order.payment_method,
                "purchased_at": order.purchased_at,
                "refunded_at": order.refunded_at,
                "status": order.status
            }
            
            # Load existing orders
            orders = self._load_orders_dict()
            orders[order.order_id] = order_dict
            
            # Encrypt and save
            config = {"orders": orders}
            encrypted_config = self.encryptor.encrypt_config(config)
            
            with open(self.ORDERS_FILE, 'w') as f:
                json.dump(encrypted_config, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save order: {e}")
            return False
    
    def _load_order(self, order_id: str) -> Optional[Order]:
        """Load a specific order."""
        orders_dict = self._load_orders_dict()
        
        if order_id not in orders_dict:
            return None
        
        order_dict = orders_dict[order_id]
        
        return Order(
            order_id=order_dict["order_id"],
            license_key=order_dict["license_key"],
            tier=order_dict["tier"],
            customer_email=order_dict["customer_email"],
            amount_paid=order_dict["amount_paid"],
            currency=order_dict["currency"],
            payment_method=order_dict["payment_method"],
            purchased_at=order_dict["purchased_at"],
            refunded_at=order_dict.get("refunded_at"),
            status=order_dict.get("status", self.STATUS_PAID)
        )
    
    def _load_orders_dict(self) -> dict:
        """Load all orders as dictionary."""
        try:
            if not os.path.exists(self.ORDERS_FILE):
                return {}
            
            with open(self.ORDERS_FILE, 'r') as f:
                encrypted_config = json.load(f)
            
            config = self.encryptor.decrypt_config(encrypted_config)
            return config.get("orders", {})
        except Exception as e:
            print(f"Failed to load orders: {e}")
            return {}
    
    def _load_all_orders(self) -> list:
        """Load all orders as Order objects."""
        orders_dict = self._load_orders_dict()
        orders = []
        
        for order_dict in orders_dict.values():
            orders.append(Order(
                order_id=order_dict["order_id"],
                license_key=order_dict["license_key"],
                tier=order_dict["tier"],
                customer_email=order_dict["customer_email"],
                amount_paid=order_dict["amount_paid"],
                currency=order_dict["currency"],
                payment_method=order_dict["payment_method"],
                purchased_at=order_dict["purchased_at"],
                refunded_at=order_dict.get("refunded_at"),
                status=order_dict.get("status", self.STATUS_PAID)
            ))
        
        return orders
    
    def _calculate_refund_amount(self, amount_paid: float) -> float:
        """Calculate refund amount after processing fee."""
        processing_fee = self._calculate_processing_fee(amount_paid)
        refund_amount = amount_paid - processing_fee
        return max(0.0, refund_amount)
    
    def _calculate_processing_fee(self, amount_paid: float) -> float:
        """Calculate processing fee (10%)."""
        return amount_paid * (self.PROCESSING_FEE_PERCENT / 100)
    
    def _save_refund_request(self, refund_request: dict) -> bool:
        """Save refund request for manual review."""
        try:
            os.makedirs("config", exist_ok=True)
            
            # Load existing requests
            requests_file = "config/refund_requests.enc"
            requests = {}
            
            if os.path.exists(requests_file):
                with open(requests_file, 'r') as f:
                    encrypted = json.load(f)
                config = self.encryptor.decrypt_config(encrypted)
                requests = config.get("refund_requests", {})
            
            # Add new request
            request_id = refund_request["refund_request_id"]
            requests[request_id] = refund_request
            
            # Save
            encrypted_config = self.encryptor.encrypt_config({"refund_requests": requests})
            with open(requests_file, 'w') as f:
                json.dump(encrypted_config, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save refund request: {e}")
            return False


class RefundGUI:
    """Simple GUI for refund processing (can be integrated into main GUI)."""
    
    def __init__(self, refund_manager: RefundManager):
        self.refund_manager = refund_manager
    
    def show_refund_dialog(self, order_id: str, customer_email: str):
        """Display refund request dialog."""
        try:
            import tkinter as tk
            from tkinter import messagebox
        except ImportError:
            print("Tkinter not available")
            return None
        
        root = tk.Tk()
        root.title("Refund Request")
        
        # Check eligibility
        is_eligible, reason = self.refund_manager.check_refund_eligibility(order_id)
        
        if not is_eligible:
            messagebox.showerror("Not Eligible", reason)
            root.destroy()
            return None
        
        # Show confirmation
        order = self.refund_manager.get_order(order_id)
        if not order:
            messagebox.showerror("Error", "Order not found")
            root.destroy()
            return None
        
        refund_amount = self.refund_manager._calculate_refund_amount(order.amount_paid)
        processing_fee = self.refund_manager._calculate_processing_fee(order.amount_paid)
        
        confirm = messagebox.askyesno(
            "Confirm Refund",
            f"Order: {order_id}\n"
            f"Amount Paid: ${order.amount_paid:.2f}\n"
            f"Processing Fee: ${processing_fee:.2f} (10%)\n"
            f"Refund Amount: ${refund_amount:.2f}\n\n"
            f"Proceed with refund?"
        )
        
        if confirm:
            # Ask for reason
            reason = messagebox.askstring("Refund Reason", "Please provide reason for refund:")
            
            if reason:
                result = self.refund_manager.request_refund(order_id, reason, customer_email)
                messagebox.showinfo("Refund Submitted", result["message"])
            else:
                messagebox.showwarning("Cancelled", "Refund request cancelled")
        
        root.destroy()
        return None


# Example usage for command-line
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python refund_manager.py <command>")
        print("Commands:")
        print("  create <license_key> <tier> <email> <amount> [currency] [payment_method]")
        print("  check <order_id>")
        print("  refund <order_id> <reason>")
        print("  request <order_id> <email> <reason>")
        sys.exit(1)
    
    rm = RefundManager()
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 6:
            print("Missing arguments")
            sys.exit(1)
        
        license_key = sys.argv[2]
        tier = sys.argv[3]
        email = sys.argv[4]
        amount = float(sys.argv[5])
        currency = sys.argv[6] if len(sys.argv) > 6 else "USD"
        payment = sys.argv[7] if len(sys.argv) > 7 else "manual"
        
        order = rm.create_order(license_key, tier, email, amount, currency, payment)
        print(f"Order created: {order.order_id}")
        print(f"License: {order.license_key}")
        print(f"Amount: ${order.amount_paid:.2f} {order.currency}")
    
    elif command == "check":
        if len(sys.argv) < 3:
            print("Missing order_id")
            sys.exit(1)
        
        order_id = sys.argv[2]
        eligible, reason = rm.check_refund_eligibility(order_id)
        print(f"Eligible: {eligible}")
        print(f"Reason: {reason}")
    
    elif command == "refund":
        if len(sys.argv) < 4:
            print("Missing arguments")
            sys.exit(1)
        
        order_id = sys.argv[2]
        reason = " ".join(sys.argv[3:])
        result = rm.process_refund(order_id, reason)
        print(json.dumps(result, indent=2))
    
    elif command == "request":
        if len(sys.argv) < 5:
            print("Missing arguments")
            sys.exit(1)
        
        order_id = sys.argv[2]
        email = sys.argv[3]
        reason = " ".join(sys.argv[4:])
        result = rm.request_refund(order_id, reason, email)
        print(json.dumps(result, indent=2))