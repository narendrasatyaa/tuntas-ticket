from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Category, Ticket, TicketComment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 1
    readonly_fields = ('created_at',)
    fields = ('author', 'comment', 'is_internal_note', 'created_at')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_id', 
        'title', 
        'category', 
        'created_by', 
        'assigned_to', 
        'colored_priority', 
        'colored_status', 
        'created_at'
    )
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('ticket_id', 'title', 'description', 'created_by__username', 'assigned_to__username')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at', 'resolved_at')
    raw_id_fields = ('created_by', 'assigned_to')
    inlines = [TicketCommentInline]

    fieldsets = (
        ('Informasi Utama', {
            'fields': ('ticket_id', 'title', 'description', 'category', 'attachment')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'priority', 'created_by', 'assigned_to')
        }),
        ('Riwayat Waktu', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',),
        }),
    )

    # Custom Badge Warna untuk Status
    @admin.display(description='Status')
    def colored_status(self, obj):
        colors = {
            'OPEN': '#dc3545',        # Red
            'IN_PROGRESS': '#ffc107', # Yellow/Amber
            'RESOLVED': '#198754',    # Green
            'CLOSED': '#6c757d',      # Gray
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#000000'),
            obj.get_status_display()
        )

    # Custom Badge Warna untuk Prioritas
    @admin.display(description='Prioritas')
    def colored_priority(self, obj):
        colors = {
            'LOW': '#0dcaf0',      # Cyan
            'MEDIUM': '#0d6efd',   # Blue
            'HIGH': '#fd7e14',     # Orange
            'URGENT': '#d63384',   # Pink/Red-Dark
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.priority, '#000000'),
            obj.get_priority_display()
        )

    # Auto update `resolved_at` ketika status diubah ke RESOLVED
    def save_model(self, request, obj, form, change):
        if change and 'status' in form.changed_data:
            if obj.status == Ticket.Status.RESOLVED and not obj.resolved_at:
                obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal_note', 'created_at')
    list_filter = ('is_internal_note', 'created_at')
    search_fields = ('ticket__ticket_id', 'comment', 'author__username')