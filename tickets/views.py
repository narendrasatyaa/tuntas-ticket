from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q

from .models import Ticket, TicketComment
from .forms import TicketCreateForm, TicketUpdateStatusForm, TicketCommentForm


class IsITStaffMixin(UserPassesTestMixin):
    """Mixin untuk memastikan hanya tim IT (is_staff=True) yang bisa mengakses view ini."""
    def test_func(self):
        return self.request.user.is_staff


class MyTicketListView(LoginRequiredMixin, ListView):
    """Daftar tiket yang diajukan oleh user yang sedang login."""
    model = Ticket
    template_name = 'tickets/my_ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_queryset(self):
        queryset = Ticket.objects.filter(created_by=self.request.user)
        
        # Filter berdasarkan status jika ada parameter URL
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset.select_related('category', 'assigned_to')


class ITQueueListView(LoginRequiredMixin, IsITStaffMixin, ListView):
    """Dashboard antrean tiket untuk tim IT Support."""
    model = Ticket
    template_name = 'tickets/it_queue_list.html'
    context_object_name = 'tickets'
    paginate_by = 15

    def get_queryset(self):
        queryset = Ticket.objects.all()
        
        # Pencarian keyword & Filter
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        assigned = self.request.GET.get('assigned')

        if q:
            queryset = queryset.filter(
                Q(ticket_id__icontains=q) | 
                Q(title__icontains=q) | 
                Q(created_by__username__icontains=q)
            )
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if assigned == 'me':
            queryset = queryset.filter(assigned_to=self.request.user)
        elif assigned == 'unassigned':
            queryset = queryset.filter(assigned_to__isnull=True)

        return queryset.select_related('category', 'created_by', 'assigned_to')


class TicketCreateView(LoginRequiredMixin, CreateView):
    """Form pengajuan tiket aduan baru."""
    model = Ticket
    form_class = TicketCreateForm
    template_name = 'tickets/ticket_form.html'
    success_url = reverse_lazy('my_tickets')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Tiket aduan Anda berhasil dibuat dan dikirim ke tim IT.")
        return super().form_valid(form)


class TicketDetailView(LoginRequiredMixin, DetailView):
    """Detail tiket, histori diskusi, dan kontrol update status."""
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'
    slug_field = 'ticket_id'
    slug_url_kwarg = 'ticket_id'

    def get_queryset(self):
        # User biasa hanya bisa lihat tiketnya sendiri, Tim IT bisa lihat semua
        if self.request.user.is_staff:
            return Ticket.objects.all()
        return Ticket.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket = self.object

        # Filter komentar (Sembunyikan catatan internal dari user biasa)
        comments = ticket.comments.all().select_related('author')
        if not self.request.user.is_staff:
            comments = comments.filter(is_internal_note=False)
            
        context['comments'] = comments
        context['comment_form'] = TicketCommentForm()
        
        # Form update status hanya untuk IT Staff
        if self.request.user.is_staff:
            context['status_form'] = TicketUpdateStatusForm(instance=ticket)

        return context


def add_comment(request, ticket_id):
    """View fungsional untuk memproses pengiriman komentar/balasan."""
    if not request.user.is_authenticated:
        return redirect('login')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    # Proteksi hak akses
    if not request.user.is_staff and ticket.created_by != request.user:
        messages.error(request, "Anda tidak memiliki akses ke tiket ini.")
        return redirect('my_tickets')

    if request.method == 'POST':
        form = TicketCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            
            # Jika user biasa, paksa internal note ke False
            if not request.user.is_staff:
                comment.is_internal_note = False
                
            comment.save()
            messages.success(request, "Catatan/balasan berhasil ditambahkan.")

    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


def assign_to_me(request, ticket_id):
    """Shortcut tombol 'Assign to Me' untuk Teknisi IT."""
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Hanya staf IT yang dapat melakukan tindakan ini.")
        return redirect('my_tickets')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    ticket.assigned_to = request.user
    
    # Otomatis ubah status ke In Progress jika masih Open
    if ticket.status == Ticket.Status.OPEN:
        ticket.status = Ticket.Status.IN_PROGRESS
        
    ticket.save()
    messages.success(request, f"Tiket {ticket.ticket_id} berhasil ditugaskan ke Anda.")
    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


def update_ticket_status(request, ticket_id):
    """View memproses form perubahan status oleh IT Support."""
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if request.method == 'POST':
        form = TicketUpdateStatusForm(request.POST, instance=ticket)
        if form.is_valid():
            updated_ticket = form.save(commit=False)
            
            # Auto set resolved_at waktu status diubah ke Resolved
            if updated_ticket.status == Ticket.Status.RESOLVED and not updated_ticket.resolved_at:
                updated_ticket.resolved_at = timezone.now()
                
            updated_ticket.save()
            messages.success(request, f"Status tiket {ticket.ticket_id} berhasil diperbarui.")

    return redirect('ticket_detail', ticket_id=ticket.ticket_id)