from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib.auth.models import User

from .models import Ticket, TicketComment, Category, UserProfile
from .forms import TicketCreateForm, TicketUpdateStatusForm, TicketCommentForm


class IsITStaffMixin(UserPassesTestMixin):
    """Mixin untuk memastikan hanya tim IT (is_staff=True) yang bisa mengakses view ini."""
    def test_func(self):
        return self.request.user.is_staff


class IsAdminUserMixin(UserPassesTestMixin):
    """Mixin untuk memastikan hanya Superuser / Admin System yang bisa mengakses view ini."""
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_superuser:
            return True
        profile = getattr(self.request.user, 'profile', None)
        return profile and profile.role == UserProfile.Role.ADMIN


class MyTicketListView(LoginRequiredMixin, ListView):
    """Dashboard Overview dengan Insight sesuai Peran Pengguna (Role-Tailored Dashboard)."""
    model = Ticket
    template_name = 'tickets/my_ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', UserProfile.Role.REQUESTER)

        # Filter queryset berdasarkan role pengguna
        if role == UserProfile.Role.REQUESTER:
            queryset = Ticket.objects.filter(created_by=user)
        elif role == UserProfile.Role.TECHNICIAN:
            queryset = Ticket.objects.filter(Q(assigned_to=user) | Q(status=Ticket.Status.OPEN))
        else:
            # IT_LEAD dan ADMIN melihat seluruh tiket
            queryset = Ticket.objects.all()

        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related('category', 'created_by', 'assigned_to')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        role = profile.role if profile else (UserProfile.Role.ADMIN if user.is_superuser else UserProfile.Role.REQUESTER)
        
        context['user_role'] = role

        # Insight Statistik khusus berdasarkan Peran (Role-Tailored Insights)
        if role == UserProfile.Role.REQUESTER:
            my_tickets = Ticket.objects.filter(created_by=user)
            context['stat_total'] = my_tickets.count()
            context['stat_open'] = my_tickets.filter(status=Ticket.Status.OPEN).count()
            context['stat_in_progress'] = my_tickets.filter(status=Ticket.Status.IN_PROGRESS).count()
            context['stat_resolved'] = my_tickets.filter(status=Ticket.Status.RESOLVED).count()

        elif role == UserProfile.Role.TECHNICIAN:
            assigned = Ticket.objects.filter(assigned_to=user)
            context['stat_total'] = assigned.count()
            context['stat_open'] = Ticket.objects.filter(status=Ticket.Status.OPEN, assigned_to__isnull=True).count()
            context['stat_in_progress'] = assigned.filter(status=Ticket.Status.IN_PROGRESS).count()
            context['stat_resolved'] = assigned.filter(status=Ticket.Status.RESOLVED).count()

        elif role == UserProfile.Role.IT_LEAD:
            all_tickets = Ticket.objects.all()
            context['stat_total'] = all_tickets.count()
            context['stat_open'] = all_tickets.filter(status=Ticket.Status.OPEN).count()
            context['stat_in_progress'] = all_tickets.filter(status=Ticket.Status.IN_PROGRESS).count()
            context['stat_resolved'] = all_tickets.filter(status=Ticket.Status.RESOLVED).count()
            context['unassigned_count'] = all_tickets.filter(assigned_to__isnull=True).count()

        else: # ADMIN
            all_tickets = Ticket.objects.all()
            context['stat_total'] = all_tickets.count()
            context['stat_open'] = all_tickets.filter(status=Ticket.Status.OPEN).count()
            context['stat_in_progress'] = all_tickets.filter(status=Ticket.Status.IN_PROGRESS).count()
            context['stat_resolved'] = all_tickets.filter(status=Ticket.Status.RESOLVED).count()
            context['total_users_count'] = User.objects.count()
            context['total_categories_count'] = Category.objects.count()

        return context


class ITQueueListView(LoginRequiredMixin, IsITStaffMixin, ListView):
    """Dashboard antrean tiket untuk tim IT Support."""
    model = Ticket
    template_name = 'tickets/it_queue_list.html'
    context_object_name = 'tickets'
    paginate_by = 15

    def get_queryset(self):
        queryset = Ticket.objects.all()
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
        if self.request.user.is_staff:
            return Ticket.objects.all()
        return Ticket.objects.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket = self.object

        comments = ticket.comments.all().select_related('author')
        if not self.request.user.is_staff:
            comments = comments.filter(is_internal_note=False)
            
        context['comments'] = comments
        context['comment_form'] = TicketCommentForm()
        
        if self.request.user.is_staff:
            context['status_form'] = TicketUpdateStatusForm(instance=ticket)

        return context


class SystemAdminView(LoginRequiredMixin, IsAdminUserMixin, TemplateView):
    """Master System & Admin View yang menyatu dengan UI Zenith (Tanpa keluar ke Django default)."""
    template_name = 'tickets/system_admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['users'] = User.objects.select_related('profile').all()
        context['roles'] = UserProfile.Role.choices
        return context


def add_comment(request, ticket_id):
    """View fungsional untuk memproses pengiriman komentar/balasan."""
    if not request.user.is_authenticated:
        return redirect('login')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if not request.user.is_staff and ticket.created_by != request.user:
        messages.error(request, "Anda tidak memiliki akses ke tiket ini.")
        return redirect('my_tickets')

    if request.method == 'POST':
        form = TicketCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            
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
            
            if updated_ticket.status == Ticket.Status.RESOLVED and not updated_ticket.resolved_at:
                updated_ticket.resolved_at = timezone.now()
                
            updated_ticket.save()
            messages.success(request, f"Status tiket {ticket.ticket_id} berhasil diperbarui.")

    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


def add_category(request):
    """Tambah Kategori Master oleh Admin di UI Zenith."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Hanya Admin System yang dapat menambah kategori.")
        return redirect('my_tickets')

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        if name:
            Category.objects.create(name=name, description=description)
            messages.success(request, f"Kategori '{name}' berhasil ditambahkan.")

    return redirect('system_admin')


def update_user_role(request, user_id):
    """Update Peran Pengguna oleh Admin di UI Zenith."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Hanya Admin System yang dapat mengubah role.")
        return redirect('my_tickets')

    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(UserProfile.Role.choices):
            profile, _ = UserProfile.objects.get_or_create(user=user_obj)
            profile.role = new_role
            profile.save()

            # Set flag is_staff otomatis untuk teknisi & lead
            if new_role in [UserProfile.Role.TECHNICIAN, UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]:
                user_obj.is_staff = True
            else:
                user_obj.is_staff = False

            if new_role == UserProfile.Role.ADMIN:
                user_obj.is_superuser = True

            user_obj.save()
            messages.success(request, f"Role untuk {user_obj.username} berhasil diubah ke {profile.get_role_display()}.")

    return redirect('system_admin')


def add_user(request):
    """Tambah User Baru oleh Admin di Master Admin Panel."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Hanya Admin System yang dapat menambah pengguna baru.")
        return redirect('my_tickets')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        department = request.POST.get('department', '').strip()
        password = request.POST.get('password', 'password123').strip()
        role = request.POST.get('role', UserProfile.Role.REQUESTER)

        if not username:
            messages.error(request, "Username wajib diisi.")
            return redirect('system_admin')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '@{username}' sudah terpakai.")
            return redirect('system_admin')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        is_staff = role in [UserProfile.Role.TECHNICIAN, UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]
        is_superuser = (role == UserProfile.Role.ADMIN)

        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={'role': role, 'department': department}
        )

        messages.success(request, f"Pengguna baru '@{username}' berhasil ditambahkan.")

    return redirect('system_admin')