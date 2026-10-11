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
    """Mixin untuk memastikan hanya Superuser, Admin System, atau IT Lead yang bisa mengakses manajemen pengguna."""
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_superuser:
            return True
        profile = getattr(self.request.user, 'profile', None)
        return profile and profile.role in [UserProfile.Role.ADMIN, UserProfile.Role.IT_LEAD]


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
            # Default untuk teknisi: tiket yang ditugaskan kepada dirinya oleh Lead
            if assigned_filter == 'all':
                queryset = Ticket.objects.all()
            else:
                queryset = Ticket.objects.filter(assigned_to=user)
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
        context['is_lead_or_admin'] = user.is_superuser or role in [UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]


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
    """Antrean tiket & tugas penanganan IT (Hanya dapat diakses staf IT)."""
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
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)
        context['is_lead_or_admin'] = user.is_superuser or role in [UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]
        context['user_role'] = role
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
        
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', None)
        context['is_lead_or_admin'] = user.is_superuser or role in [UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]
        context['user_role'] = role

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

    # Jika tiket sudah selesai / Done (RESOLVED atau CLOSED), pelapor/user tidak dapat mengedit lagi
    if not request.user.is_staff and ticket.status in [Ticket.Status.RESOLVED, Ticket.Status.CLOSED]:
        messages.error(request, f"Tiket {ticket.ticket_id} sudah berstatus {ticket.get_status_display()} dan tidak dapat diubah lagi.")
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)

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


# USER CRUD (Create, Read, Update, Delete) - Admin & IT Lead
def add_user(request):
    """CREATE User oleh Admin atau IT Lead."""
    if not request.user.is_authenticated:
        return redirect('login')

    current_profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (current_profile and current_profile.role == UserProfile.Role.ADMIN)
    is_lead = (current_profile and current_profile.role == UserProfile.Role.IT_LEAD)

    if not (is_admin or is_lead):
        messages.error(request, "Hanya Admin System atau IT Lead yang dapat menambah pengguna baru.")
        return redirect('my_tickets')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        department = request.POST.get('department', '').strip()
        password = request.POST.get('password', 'password123').strip()
        role = request.POST.get('role', UserProfile.Role.REQUESTER)

        # IT Lead hanya dapat membuat akun Karyawan atau Teknisi
        if is_lead and not is_admin:
            if role in [UserProfile.Role.ADMIN, UserProfile.Role.IT_LEAD]:
                messages.error(request, "IT Lead hanya memiliki wewenang membuat akun Karyawan (Requester) atau Teknisi.")
                return redirect('system_admin')

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

        messages.success(request, f"Pengguna baru '@{username}' ({role}) berhasil ditambahkan.")

    return redirect('system_admin')


def edit_user(request, user_id):
    """UPDATE User oleh Admin atau IT Lead (Edit detail & password)."""
    if not request.user.is_authenticated:
        return redirect('login')

    current_profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (current_profile and current_profile.role == UserProfile.Role.ADMIN)
    is_lead = (current_profile and current_profile.role == UserProfile.Role.IT_LEAD)

    if not (is_admin or is_lead):
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    user_obj = get_object_or_404(User, id=user_id)
    target_profile = getattr(user_obj, 'profile', None)

    # IT Lead tidak boleh mengedit akun Admin
    if is_lead and not is_admin:
        if user_obj.is_superuser or (target_profile and target_profile.role == UserProfile.Role.ADMIN):
            messages.error(request, "IT Lead tidak dapat mengubah data akun Administrator.")
            return redirect('system_admin')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        department = request.POST.get('department', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role')

        # IT Lead tidak boleh menaikkan peran ke Admin/Lead
        if is_lead and not is_admin:
            if role in [UserProfile.Role.ADMIN, UserProfile.Role.IT_LEAD]:
                messages.error(request, "IT Lead hanya berwenang menetapkan peran Teknisi atau Karyawan.")
                return redirect('system_admin')

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
    """DELETE User oleh Admin (Hanya Superuser/Admin System)."""
    if not request.user.is_authenticated:
        return redirect('login')

    current_profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (current_profile and current_profile.role == UserProfile.Role.ADMIN)

    if not is_admin:
        messages.error(request, "Hanya Administrator System yang memiliki hak menghapus akun.")
        return redirect('system_admin')

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
    if not request.user.is_authenticated:
        return redirect('login')

    current_profile = getattr(request.user, 'profile', None)
    is_admin = request.user.is_superuser or (current_profile and current_profile.role == UserProfile.Role.ADMIN)
    is_lead = (current_profile and current_profile.role == UserProfile.Role.IT_LEAD)

    if not (is_admin or is_lead):
        messages.error(request, "Akses ditolak.")
        return redirect('my_tickets')

    user_obj = get_object_or_404(User, id=user_id)
    target_profile = getattr(user_obj, 'profile', None)

    if is_lead and not is_admin:
        if user_obj.is_superuser or (target_profile and target_profile.role == UserProfile.Role.ADMIN):
            messages.error(request, "IT Lead tidak dapat mengubah role akun Administrator.")
            return redirect('system_admin')

    if request.method == 'POST':
        new_role = request.POST.get('role')
        if is_lead and not is_admin and new_role in [UserProfile.Role.ADMIN, UserProfile.Role.IT_LEAD]:
            messages.error(request, "IT Lead hanya dapat mengubah peran antara Teknisi atau Karyawan.")
            return redirect('system_admin')

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
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    role = getattr(getattr(user, 'profile', None), 'role', None)
    is_lead_or_admin = user.is_superuser or role in [UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]

    if not is_lead_or_admin:
        messages.error(request, "Akses ditolak: Teknisi tidak dapat mengambil tiket sendiri. Penugasan hanya dilakukan oleh IT Lead / Supervisor.")
        return redirect('my_tickets')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    ticket.assigned_to = request.user
    
    if ticket.status == Ticket.Status.OPEN:
        ticket.status = Ticket.Status.IN_PROGRESS
        
    ticket.save()
    messages.success(request, f"Tiket {ticket.ticket_id} berhasil dialokasikan.")
    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


def update_ticket_status(request, ticket_id):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, "Akses ditolak. Hanya staff/admin yang dapat mengubah tiket.")
        return redirect('my_tickets')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    user = request.user
    role = getattr(getattr(user, 'profile', None), 'role', None)
    is_lead_or_admin = user.is_superuser or role in [UserProfile.Role.IT_LEAD, UserProfile.Role.ADMIN]

    if request.method == 'POST':
        status_val = request.POST.get('status')
        priority_val = request.POST.get('priority')
        assigned_to_id = request.POST.get('assigned_to')

        if status_val and status_val in dict(Ticket.Status.choices):
            ticket.status = status_val
            if status_val == Ticket.Status.RESOLVED and not ticket.resolved_at:
                ticket.resolved_at = timezone.now()

        # Update prioritas hanya oleh Lead / Admin
        if priority_val and priority_val in dict(Ticket.Priority.choices):
            if is_lead_or_admin:
                ticket.priority = priority_val

        # Resolution note capture saat staff IT resolve tiket
        resolution_note = request.POST.get('resolution_note')
        if resolution_note is not None and resolution_note.strip():
            ticket.resolution_note = resolution_note.strip()

        # Update assignment: HANYA BOLEH OLEH IT LEAD / ADMIN!
        if 'assigned_to' in request.POST:
            if not is_lead_or_admin:
                messages.error(request, "Akses ditolak: Penugasan tiket (Assign To) hanya wewenang IT Lead / Supervisor.")
            else:
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
                        messages.success(request, f"Tiket {ticket.ticket_id} berhasil ditugaskan ke @{assigned_user.username} oleh Lead.")
                    else:
                        messages.error(request, "User teknisi tidak ditemukan.")

        ticket.save()

    next_url = request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


def submit_rating(request, ticket_id):
    """Karyawan memberi rating kepuasan CSAT (1-5 Bintang) dan ulasan untuk tiket yang diselesaikan."""
    if not request.user.is_authenticated:
        return redirect('login')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    # Hanya pelapor (created_by) atau admin yang bisa memberi rating
    if ticket.created_by != request.user and not request.user.is_superuser:
        messages.error(request, "Hanya pelapor tiket yang dapat memberikan penilaian kepuasan.")
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)

    if ticket.status not in [Ticket.Status.RESOLVED, Ticket.Status.CLOSED]:
        messages.error(request, "Penilaian hanya dapat diberikan setelah tiket diselesaikan oleh tim IT.")
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)

    if request.method == 'POST':
        try:
            rating_val = int(request.POST.get('rating', 5))
            if 1 <= rating_val <= 5:
                ticket.rating = rating_val
                ticket.rating_feedback = request.POST.get('rating_feedback', '').strip()
                ticket.rated_at = timezone.now()
                ticket.status = Ticket.Status.CLOSED
                ticket.save()
                messages.success(request, "Terima kasih banyak! Penilaian dan ulasan kepuasan Anda berhasil disimpan.")
            else:
                messages.error(request, "Nilai rating harus antara 1 sampai 5 bintang.")
        except ValueError:
            messages.error(request, "Format rating tidak valid.")

    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


def reopen_ticket(request, ticket_id):
    """Karyawan membuka kembali tiket yang telah di-resolve jika kendala belum tuntas teratasi."""
    if not request.user.is_authenticated:
        return redirect('login')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if ticket.created_by != request.user and not request.user.is_staff:
        messages.error(request, "Hanya pelapor tiket yang dapat membuka kembali tiket ini.")
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)

    if request.method == 'POST':
        reason = request.POST.get('reopen_reason', '').strip()
        if not reason:
            messages.error(request, "Harap sertakan alasan mengapa tiket dibuka kembali.")
            return redirect('ticket_detail', ticket_id=ticket.ticket_id)

        # Ubah status kembali ke IN_PROGRESS
        ticket.status = Ticket.Status.IN_PROGRESS
        ticket.resolved_at = None
        ticket.save()

        # Catat ke riwayat komentar tiket
        TicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            comment=f"[TIKET DIBUKA KEMBALI OLEH PELAPOR]\nAlasan: {reason}",
            is_internal_note=False
        )

        messages.warning(request, f"Tiket {ticket.ticket_id} telah dibuka kembali. Tim IT akan segera menindaklanjuti kendala Anda.")

    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


def close_ticket(request, ticket_id):
    """Karyawan mengonfirmasi tiket tuntas dan menutup tiket secara resmi."""
    if not request.user.is_authenticated:
        return redirect('login')

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if ticket.created_by != request.user and not request.user.is_staff:
        messages.error(request, "Akses ditolak.")
        return redirect('ticket_detail', ticket_id=ticket.ticket_id)

    if request.method == 'POST':
        ticket.status = Ticket.Status.CLOSED
        ticket.save()
        messages.success(request, f"Tiket {ticket.ticket_id} resmi ditutup. Terima kasih atas konfirmasi Anda.")

    return redirect('ticket_detail', ticket_id=ticket.ticket_id)


def switch_user_role(request, username):
    """Switch akun instan tanpa perlu ketik password untuk Admin & Switch Role demo."""
    target_user = get_object_or_404(User, username=username)
    auth_login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')
    
    profile = getattr(target_user, 'profile', None)
    role_name = profile.get_role_display() if profile else target_user.username
    messages.success(request, f"Berhasil beralih akun ke: @{target_user.username} ({role_name})")
    return redirect('my_tickets')


class ReportView(LoginRequiredMixin, IsITStaffMixin, TemplateView):
    """View untuk pratinjau analitik dan laporan evaluasi kinerja penanganan IT sebelum diekspor."""
    template_name = 'tickets/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user_id = self.request.GET.get('user_id', '')
        status_filter = self.request.GET.get('status', '')
        category_id = self.request.GET.get('category_id', '')
        priority_filter = self.request.GET.get('priority', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        q = self.request.GET.get('q', '')

        queryset = Ticket.objects.select_related('created_by', 'assigned_to', 'category').all()

        if user_id:
            queryset = queryset.filter(Q(assigned_to_id=user_id) | Q(created_by_id=user_id))
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if q:
            queryset = queryset.filter(
                Q(ticket_id__icontains=q) |
                Q(title__icontains=q) |
                Q(created_by__username__icontains=q) |
                Q(created_by__first_name__icontains=q) |
                Q(assigned_to__username__icontains=q) |
                Q(assigned_to__first_name__icontains=q)
            )

        total_tickets = queryset.count()
        resolved_tickets = queryset.filter(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]).count()
        open_tickets = queryset.filter(status=Ticket.Status.OPEN).count()
        in_progress_tickets = queryset.filter(status=Ticket.Status.IN_PROGRESS).count()

        # CSAT Analysis
        rated_qs = queryset.filter(rating__isnull=False)
        rated_count = rated_qs.count()
        avg_rating = round(sum(t.rating for t in rated_qs) / rated_count, 1) if rated_count > 0 else 0

        # SLA Compliance & Duration
        resolved_list = queryset.filter(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
        sla_met_count = 0
        sla_breached_count = 0
        total_duration_seconds = 0
        valid_duration_count = 0

        for t in resolved_list:
            if t.due_date and t.resolved_at:
                if t.resolved_at <= t.due_date:
                    sla_met_count += 1
                else:
                    sla_breached_count += 1
            if t.resolved_at and t.created_at:
                delta = (t.resolved_at - t.created_at).total_seconds()
                if delta > 0:
                    total_duration_seconds += delta
                    valid_duration_count += 1

        sla_rate = round((sla_met_count / resolved_tickets * 100), 1) if resolved_tickets > 0 else 100.0
        avg_duration_hours = round((total_duration_seconds / valid_duration_count) / 3600, 1) if valid_duration_count > 0 else 0

        # Master Data for Filter Dropdowns
        technicians = User.objects.filter(is_staff=True).order_by('first_name', 'username')
        categories = Category.objects.all().order_by('name')

        # Limit preview to recent 200 items for responsive display
        preview_tickets = queryset.order_by('-created_at')[:200]

        # Preserve query string for export button
        query_dict = self.request.GET.copy()
        export_query = query_dict.urlencode()

        context.update({
            'tickets': preview_tickets,
            'total_tickets': total_tickets,
            'resolved_tickets': resolved_tickets,
            'open_tickets': open_tickets,
            'in_progress_tickets': in_progress_tickets,
            'sla_compliance_rate': sla_rate,
            'sla_met_count': sla_met_count,
            'sla_breached_count': sla_breached_count,
            'avg_csat': avg_rating,
            'rated_count': rated_count,
            'avg_duration_hours': avg_duration_hours,
            'technicians': technicians,
            'categories': categories,
            'statuses': Ticket.Status.choices,
            'priorities': Ticket.Priority.choices,
            'selected_user_id': user_id,
            'selected_status': status_filter,
            'selected_category_id': category_id,
            'selected_priority': priority_filter,
            'selected_start_date': start_date,
            'selected_end_date': end_date,
            'search_q': q,
            'export_query': export_query,
            'printed_at': timezone.now(),
        })
        return context


def export_tickets_report(request):
    """View untuk mengunduh laporan CSV / Excel dengan dukungan filter data lengkap."""
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Akses ditolak. Hanya staff/admin yang dapat mengunduh laporan.")
        return redirect('my_tickets')

    user_id = request.GET.get('user_id', '')
    status_filter = request.GET.get('status', '')
    category_id = request.GET.get('category_id', '')
    priority_filter = request.GET.get('priority', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    q = request.GET.get('q', '')
    
    queryset = Ticket.objects.select_related('created_by', 'assigned_to', 'category').all()

    target_name = "Semua"
    if user_id:
        target_user = get_object_or_404(User, pk=user_id)
        queryset = queryset.filter(Q(assigned_to=target_user) | Q(created_by=target_user))
        target_name = target_user.get_full_name() or target_user.username

    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)
    if start_date:
        queryset = queryset.filter(created_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__date__lte=end_date)
    if q:
        queryset = queryset.filter(
            Q(ticket_id__icontains=q) |
            Q(title__icontains=q) |
            Q(created_by__username__icontains=q) |
            Q(created_by__first_name__icontains=q) |
            Q(assigned_to__username__icontains=q) |
            Q(assigned_to__first_name__icontains=q)
        )

    clean_target = "".join(c for c in target_name if c.isalnum() or c in ('_', '-'))
    filename = f"Laporan_Penilaian_IT_{clean_target}_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Tulis UTF-8 BOM agar Microsoft Excel membuka karakter dengan benar
    response.write('\ufeff'.encode('utf-8'))

    writer = csv.writer(response)
    
    # Header Dokumen & Metadata
    writer.writerow(["LAPORAN PENILAIAN PERFORMA IT & TIKET ADUAN KARYAWAN - TUNTAS DESK"])
    writer.writerow([f"Tanggal Cetak/Export: {timezone.now().strftime('%d %b %Y, %H:%M WIB')}"])
    writer.writerow([f"Filter Pengguna: {target_name}"])
    writer.writerow([f"Total Tiket Terdaftar: {queryset.count()}"])
    writer.writerow([])  # Baris pemisah kosong

    # Header Kolom Data
    writer.writerow([
        "ID Tiket", 
        "Judul Masalah / Aduan", 
        "Kategori Kendala", 
        "Tingkat Prioritas", 
        "Status Penanganan", 
        "Pelapor (Karyawan)", 
        "Teknisi Penanggung Jawab", 
        "Waktu Pengajuan", 
        "Batas Waktu SLA",
        "Waktu Selesai (Resolved)",
        "Kepatuhan SLA",
        "Durasi Penanganan (Jam)",
        "Catatan Solusi Perbaikan",
        "Rating Kepuasan (CSAT)",
        "Ulasan / Masukan Karyawan"
    ])

    for t in queryset.order_by('-created_at'):
        durasi_jam = "-"
        if t.resolved_at and t.created_at:
            delta = t.resolved_at - t.created_at
            durasi_jam = round(delta.total_seconds() / 3600, 2)

        # Status kepatuhan SLA
        sla_status = "-"
        if t.due_date:
            if t.resolved_at:
                sla_status = "Tepat Waktu (SLA Met)" if t.resolved_at <= t.due_date else "Terlambat (SLA Breached)"
            elif t.status in [Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]:
                sla_status = "Dalam Batas Waktu" if not t.is_sla_breached else "Terlambat (SLA Breached)"

        rating_display = f"{t.rating} Bintang" if t.rating else "Belum Dinilai"

        writer.writerow([
            t.ticket_id,
            t.title,
            t.category.name if t.category else "-",
            t.get_priority_display(),
            t.get_status_display(),
            t.created_by.get_full_name() or t.created_by.username,
            (t.assigned_to.get_full_name() or t.assigned_to.username) if t.assigned_to else "Belum Ditugaskan",
            t.created_at.strftime("%Y-%m-%d %H:%M"),
            t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else "-",
            t.resolved_at.strftime("%Y-%m-%d %H:%M") if t.resolved_at else "-",
            sla_status,
            durasi_jam,
            t.resolution_note or "-",
            rating_display,
            t.rating_feedback or "-"
        ])

    return response