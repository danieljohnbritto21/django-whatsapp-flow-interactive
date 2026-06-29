from django import forms
from .models import Donation


class DonationForm(forms.ModelForm):
    """Form for processing WhatsApp donation submissions"""
    
    class Meta:
        model = Donation
        fields = ['cause', 'amount', 'full_name', 'mobile_number', 'email', 'message']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set cause field with choices
        self.fields['cause'].widget = forms.Select(choices=Donation.CAUSE_CHOICES)
        self.fields['cause'].widget.attrs.update({
            'class': 'form-control',
            'id': 'donation-cause'
        })
        
        # Make message optional
        self.fields['message'].required = False
        
        # Add placeholders and styling to all fields
        self.fields['full_name'].widget.attrs.update({
            'placeholder': 'Enter your full name',
            'class': 'form-control',
            'id': 'donor-name',
            'required': 'required'
        })
        
        self.fields['mobile_number'].widget.attrs.update({
            'placeholder': 'Enter 10-digit mobile number',
            'class': 'form-control',
            'id': 'donor-mobile',
            'required': 'required',
            'maxlength': '10',
            'pattern': '[6-9][0-9]{9}'
        })
        
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Enter your email address',
            'class': 'form-control',
            'id': 'donor-email',
            'required': 'required',
            'type': 'email'
        })
        
        self.fields['amount'].widget.attrs.update({
            'placeholder': 'Enter donation amount in INR',
            'class': 'form-control',
            'id': 'donation-amount',
            'required': 'required',
            'min': '1',
            'step': '1'
        })
        
        self.fields['message'].widget.attrs.update({
            'placeholder': 'Any special message (optional)',
            'class': 'form-control',
            'id': 'donor-message',
            'rows': '3'
        })
        
        # Add labels
        self.fields['cause'].label = 'Donation Cause'
        self.fields['amount'].label = 'Donation Amount (₹)'
        self.fields['full_name'].label = 'Full Name'
        self.fields['mobile_number'].label = 'Mobile Number'
        self.fields['email'].label = 'Email Address'
        self.fields['message'].label = 'Message (Optional)'
    
    def clean_mobile_number(self):
        """Validate Indian mobile number"""
        mobile = self.cleaned_data.get('mobile_number')
        
        if not mobile:
            raise forms.ValidationError("Mobile number is required")
        
        # Remove any spaces or special characters
        mobile = ''.join(filter(str.isdigit, mobile))
        
        # Indian mobile number validation
        import re
        if not re.match(r'^[6-9]\d{9}$', mobile):
            raise forms.ValidationError(
                "Please enter a valid 10-digit Indian mobile number starting with 6,7,8, or 9"
            )
        
        return mobile
    
    def clean_email(self):
        """Validate email address"""
        email = self.cleaned_data.get('email')
        
        if not email:
            raise forms.ValidationError("Email address is required")
        
        # Additional email validation
        if '@' not in email or '.' not in email:
            raise forms.ValidationError("Please enter a valid email address")
        
        return email.strip().lower()
    
    def clean_amount(self):
        """Validate donation amount"""
        amount = self.cleaned_data.get('amount')
        
        if amount is None:
            raise forms.ValidationError("Donation amount is required")
        
        if amount <= 0:
            raise forms.ValidationError("Donation amount must be greater than zero")
        
        if amount > 10000000:  # 1 crore limit
            raise forms.ValidationError("Donation amount cannot exceed ₹1,00,00,000")
        
        return amount
    
    def clean_full_name(self):
        """Validate donor name"""
        name = self.cleaned_data.get('full_name')
        
        if not name or len(name.strip()) == 0:
            raise forms.ValidationError("Full name is required")
        
        if len(name.strip()) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long")
        
        return name.strip()
    
    def clean_message(self):
        """Clean and validate optional message"""
        message = self.cleaned_data.get('message', '')
        
        if message:
            # Limit message length
            if len(message) > 500:
                raise forms.ValidationError("Message cannot exceed 500 characters")
        
        return message.strip()