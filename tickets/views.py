import csv
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login as auth_login
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
        assigned_filter = self.request.GET.get('assigned')

        if assigned_filter == 'me':
            queryset = Ticket.objects.filter(assigned_to=user)
        elif assigned_filter == 'created':
            queryset = Ticket.objects.filter(created_by=user)
        elif role == UserProfile.Role.REQUESTER:
            queryset = Ticket.objects.filter(created_by=user)
        elif role == UserProfile.Role.TECHNICIAN:
            queryset = Ticket.objects.filter(Q(assigned_to=user) | Q(status=Ticket.Status.OPEN))
        else:
            queryset = Ticket.objects.all()

        if assigned_filter == 'unassigned':
            queryset = queryset.filter(assigned_to__isnull=True)

        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related('category', 'created_by', 'assigned_to').order_by('-created_at')


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, 'profile', None)
        role = profile.role if profile else (UserProfile.Role.ADMIN if user.is_superuser else UserProfile.Role.REQUESTER)
        
        context['user_role'] = role
        context['my_assigned_count'] = Ticket.objects.filter(assigned_to=user).count()


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


class ITQueueListView(LoginRequiredMixin, ListView):
    """Antrean tiket & tugas penanganan IT (Clean Task List View)."""
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['staff_users'] = User.objects.filter(is_staff=True)
        return context

# TICKET CRUD (Create, Read, Update, Delete)

class TicketCreateView(LoginRequiredMixin, CreateView):
    """Form pengajuan tiket aduan baru (CREATE Ticket)."""
    model = Ticket
    form_class = TicketCreateForm
    template_name = 'tickets/ticket_form.html'
    success_url = reverse_lazy('my_tickets')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Tiket aduan Anda berhasil dibuat dan dikirim ke tim IT.")
        return super().form_valid(form)


class TicketDetailView(LoginRequiredMixin, DetailView):
    """Detail tiket & histori diskusi (READ Ticket)."""
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
            context['staff_users'] = User.objects.filter(is_staff=True)

        return context



def edit_ticket(request, ticket_id):
    """Edit Tiket Aduan (UPDATE Ticket). Pembuat tiket atau Staff IT bisa mengedit."""
    if not request.user.is_authenticated:
        return redirect('login')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    # Permission check: Pembuat tiket atau Tim IT/Admin
    if not request.user.is_staff and ticket.created_by != request.user:
        messages.error(request, "Anda tidak memiliki izin untuk mengedit tiket ini.")
        return redirect('my_tickets')

    if request.method == 'POST':
        form = TicketCreateForm(request.POST, request.FILES, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f"Tiket {ticket.ticket_id} berhasil diperbarui.")
            return redirect('ticket_detail', ticket_id=ticket.ticket_id)
    else:
        form = TicketCreateForm(instance=ticket)

    return render(request, 'tickets/ticket_form.html', {
        'form': form,
        'ticket': ticket,
        'is_edit': True
    })


def delete_ticket(request, ticket_id):
    """Hapus Tiket Aduan (DELETE Ticket). Requester bisa hapus jika status OPEN, IT/Admin bisa hapus kapan pun."""
    if not request.user.is_authenticated:
        return redirect('login')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if not request.user.is_staff and (ticket.created_by != request.user or ticket.status != Ticket.Status.OPEN):
        messages.error(request, "Anda tidak dapat menghapus tiket ini.")
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)

    if request.method == 'POST':
        ticket.delete()
        messages.success(request, f"Tiket {ticket_id} berhasil dihapus.")
        return redirect('my_tickets')

    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


# MASTER SYSTEM ADMIN PANEL VIEW

class SystemAdminView(LoginRequiredMixin, IsAdminUserMixin, TemplateView):
    """Master System & Admin View yang menyatu dengan UI Zenith/Unfold."""
    template_name = 'tickets/system_admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['users'] = User.objects.select_related('profile').all()
        context['tickets'] = Ticket.objects.select_related('created_by', 'assigned_to', 'category').all().order_by('-created_at')
        context['staff_users'] = User.objects.filter(is_staff=True)
        context['roles'] = UserProfile.Role.choices
        return context


# USER CRUD (Create, Read, Update, Delete) - Admin Only

def add_user(request):
    """CREATE User oleh Admin."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
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


def edit_user(request, user_id):
    """UPDATE User oleh Admin (Edit detail & password)."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        department = request.POST.get('department', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role')

        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.email = email

        if password:
            user_obj.set_password(password)

        if role in dict(UserProfile.Role.choices):
            profile, _ = UserProfile.objects.get_or_create(user=user_obj)
            profile.role = role
            profile.department = department
            profile.save()

            user_obj.is_staff = role in [UserProfile.Role.TECHNICIAN, UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]
            user_obj.is_superuser = (role == UserProfile.Role.ADMIN)

        user_obj.save()
        messages.success(request, f"Data pengguna @{user_obj.username} berhasil diperbarui.")

    return redirect('system_admin')


def delete_user(request, user_id):
    """DELETE User oleh Admin."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    user_obj = get_object_or_404(User, id=user_id)

    if user_obj == request.user:
        messages.error(request, "Anda tidak dapat menghapus akun Anda sendiri.")
        return redirect('system_admin')

    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        messages.success(request, f"Pengguna @{username} berhasil dihapus.")

    return redirect('system_admin')


def update_user_role(request, user_id):
    """Quick update Peran (Role) pengguna dari dropdown."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(UserProfile.Role.choices):
            profile, _ = UserProfile.objects.get_or_create(user=user_obj)
            profile.role = new_role
            profile.save()

            user_obj.is_staff = new_role in [UserProfile.Role.TECHNICIAN, UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]
            user_obj.is_superuser = (new_role == UserProfile.Role.ADMIN)

            user_obj.save()
            messages.success(request, f"Role untuk @{user_obj.username} diubah ke {profile.get_role_display()}.")

    return redirect('system_admin')


# CATEGORY CRUD (Create, Read, Update, Delete) - Admin Only

def add_category(request):
    """CREATE Kategori Tiket."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            Category.objects.create(name=name, description=description)
            messages.success(request, f"Kategori '{name}' berhasil ditambahkan.")

    return redirect('system_admin')


def edit_category(request, category_id):
    """UPDATE Kategori Tiket."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    cat = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') in ['on', 'true', True]

        if name:
            cat.name = name
            cat.description = description
            cat.is_active = is_active
            cat.save()
            messages.success(request, f"Kategori '{name}' berhasil diperbarui.")

    return redirect('system_admin')


def delete_category(request, category_id):
    """DELETE Kategori Tiket."""
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    cat = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        name = cat.name
        cat.delete()
        messages.success(request, f"Kategori '{name}' berhasil dihapus.")

    return redirect('system_admin')



# Helper Ticket Actions
def add_comment(request, ticket_id):
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
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Akses ditolak. Hanya staff/admin yang dapat mengubah penugasan.")
        return redirect('my_tickets')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if request.method == 'POST':
        status_val = request.POST.get('status')
        priority_val = request.POST.get('priority')
        assigned_to_id = request.POST.get('assigned_to')

        if status_val and status_val in dict(Ticket.Status.choices):
            ticket.status = status_val
            if status_val == Ticket.Status.RESOLVED and not ticket.resolved_at:
                ticket.resolved_at = timezone.now()

        if priority_val and priority_val in dict(Ticket.Priority.choices):
            ticket.priority = priority_val

        # Update assignment if assigned_to field is present in request.POST
        if 'assigned_to' in request.POST:
            if not assigned_to_id or assigned_to_id == '':
                ticket.assigned_to = None
                messages.success(request, f"Penugasan teknisi untuk tiket {ticket.ticket_id} dikosongkan.")
            else:
                assigned_user = User.objects.filter(id=assigned_to_id).first()
                if assigned_user:
                    if not assigned_user.is_staff:
                        assigned_user.is_staff = True
                        assigned_user.save()
                    ticket.assigned_to = assigned_user
                    if ticket.status == Ticket.Status.OPEN:
                        ticket.status = Ticket.Status.IN_PROGRESS
                    messages.success(request, f"Tiket {ticket.ticket_id} berhasil ditugaskan ke @{assigned_user.username}.")
                else:
                    messages.error(request, "User teknisi tidak ditemukan.")

        ticket.save()

    next_url = request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('ticket_detail', ticket_id=ticket.ticket_id)




def switch_user_role(request, username):
    """Switch akun instan tanpa perlu ketik password untuk Admin & Switch Role demo."""
    target_user = get_object_or_404(User, username=username)
    auth_login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    
    profile = getattr(target_user, 'profile', None)
    role_name = profile.get_role_display() if profile else target_user.username
    messages.success(request, f"Berhasil beralih akun ke: @{target_user.username} ({role_name})")
    return redirect('my_tickets')


def export_tickets_report(request):
    """View untuk mengunduh laporan CSV (General & Per-Karyawan/Teknisi) untuk penilaian akhir."""
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Akses ditolak. Hanya staff/admin yang dapat mengunduh laporan.")
        return redirect('my_tickets')

    user_id = request.GET.get('user_id')
    status_filter = request.GET.get('status')
    
    queryset = Ticket.objects.select_related('created_by', 'assigned_to', 'category').all()

    target_name = "General_System"
    if user_id:
        target_user = get_object_or_404(User, pk=user_id)
        queryset = queryset.filter(Q(created_by=target_user) | Q(assigned_to=target_user))
        target_name = target_user.username

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    filename = f"Laporan_Penilaian_IT_{target_name}_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Write UTF-8 BOM so Excel opens cleanly
    response.write('\ufeff'.encode('utf-8'))

    writer = csv.writer(response)
    
    # Summary Info Header
    writer.writerow(["LAPORAN PENILAIAN PERFORMA IT & TIKET ADUAN KARYAWAN - TUNTAS DESK"])
    writer.writerow([f"Tanggal Export: {timezone.now().strftime('%d %b %Y, %H:%M WIB')}", f"Filter Target: {target_name}"])
    writer.writerow([f"Total Tiket Terdaftar: {queryset.count()}"])
    writer.writerow([]) # Empty separator line

    # Column Headers
    writer.writerow([
        "ID Tiket", 
        "Judul Masalah / Aduan", 
        "Kategori Kendala", 
        "Tingkat Prioritas", 
        "Status Penanganan", 
        "Pelapor (Karyawan)", 
        "Teknisi Penanggung Jawab", 
        "Waktu Pengajuan", 
        "Waktu Selesai (Resolved)",
        "Durasi Penanganan (Jam)"
    ])

    for t in queryset:
        durasi_jam = "-"
        if t.resolved_at and t.created_at:
            delta = t.resolved_at - t.created_at
            durasi_jam = round(delta.total_seconds() / 3600, 2)

        writer.writerow([
            t.ticket_id,
            t.title,
            t.category.name if t.category else "-",
            t.get_priority_display(),
            t.get_status_display(),
            t.created_by.get_full_name() or t.created_by.username,
            (t.assigned_to.get_full_name() or t.assigned_to.username) if t.assigned_to else "Belum Ditugaskan",
            t.created_at.strftime("%Y-%m-%d %H:%M"),
            t.resolved_at.strftime("%Y-%m-%d %H:%M") if t.resolved_at else "-",
            durasi_jam
        ])

    return response