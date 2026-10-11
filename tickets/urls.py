from django.urls import path
from . import views

urlpatterns = [
    # 1. Dashboards & Static Navigation Routes (Must come FIRST)
    path('my-tickets/', views.MyTicketListView.as_view(), name='my_tickets'),
    path('it-queue/', views.ITQueueListView.as_view(), name='it_queue'),
    path('reports/', views.ReportView.as_view(), name='reports_view'),
    path('create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('switch-role/<str:username>/', views.switch_user_role, name='switch_role'),

    # 2. Master System Admin Panel & Admin CRUD Routes (Must come BEFORE <str:ticket_id>/)
    path('system-admin/', views.SystemAdminView.as_view(), name='system_admin'),
    path('system-admin/export-report/', views.export_tickets_report, name='export_report'),
    path('system-admin/user/add/', views.add_user, name='add_user'),
    path('system-admin/user/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('system-admin/user/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('system-admin/user/<int:user_id>/role/', views.update_user_role, name='update_user_role'),

    path('system-admin/category/add/', views.add_category, name='add_category'),
    path('system-admin/category/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('system-admin/category/<int:category_id>/delete/', views.delete_category, name='delete_category'),

    # 3. Dynamic Ticket Parameter Routes (Must come LAST)
    path('<str:ticket_id>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('<str:ticket_id>/edit/', views.edit_ticket, name='ticket_edit'),
    path('<str:ticket_id>/delete/', views.delete_ticket, name='ticket_delete'),
    path('<str:ticket_id>/comment/', views.add_comment, name='add_comment'),
    path('<str:ticket_id>/assign-me/', views.assign_to_me, name='assign_to_me'),
    path('<str:ticket_id>/update-status/', views.update_ticket_status, name='update_ticket_status'),
    path('<str:ticket_id>/rate/', views.submit_rating, name='submit_rating'),
    path('<str:ticket_id>/reopen/', views.reopen_ticket, name='reopen_ticket'),
    path('<str:ticket_id>/close/', views.close_ticket, name='close_ticket'),
]