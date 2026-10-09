from django import forms

from .models import Category, Order, Product


class DashboardProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("name", "description", "price", "stock", "image", "category")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "price": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "stock": forms.NumberInput(attrs={"min": "0", "step": "1"}),
        }


class DashboardCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name",)


class InventoryStockForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("stock",)
        widgets = {"stock": forms.NumberInput(attrs={"min": "0", "step": "1"})}


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ("status",)
