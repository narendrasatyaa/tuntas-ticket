from django.urls import path
from . import views

urlpatterns = [
    path('my-tickets/', views.MyTicketListView.as_view(), name='my_tickets'),
    path('it-queue/', views.ITQueueListView.as_view(), name='it_queue'),
    path('create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('<str:ticket_id>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('<str:ticket_id>/comment/', views.add_comment, name='add_comment'),
    path('<str:ticket_id>/assign-me/', views.assign_to_me, name='assign_to_me'),
    path('<str:ticket_id>/update-status/', views.update_ticket_status, name='update_ticket_status'),
]