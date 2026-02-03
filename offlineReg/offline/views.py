from django.shortcuts import render, redirect
from .forms import RegistrationForm
from .models import Registration, Event,head
from django.shortcuts import render
from .models import Category, Event
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Category, Event, Registration
from .forms import RegistrationForm
import json
@login_required
def register(request):
    if request.user.is_superuser:
        categories = Category.objects.all()
        events = Event.objects.all()
        events_json = {
            category.id: [{"id": event.id, "name": event.name} for event in category.events.all()]
            for category in categories
        }

        if request.method == "POST":
            form = RegistrationForm(request.POST)
            if form.is_valid():
                # Save the form instance
                registration = form.save(commit=False)
                # Ensure the event selected is valid (you can validate further if needed)
                registration.event = Event.objects.get(name=form.cleaned_data["event"])
                if registration.email[0].isdigit():
                    registration.email += "@mits.ac.in"
                else:
                    registration.email += "@gmail.com"
                registration.save()
                # Display a success message
                messages.success(request, "Registration successful!")
                return redirect("register")  # Redirect to the same page or another page
            else:
                messages.error(request, "Please correct the errors in the form.")

        context = {
            "categories": categories,
            "events_json": json.dumps(events_json),
            "form": RegistrationForm(),
        }
        return render(request, "register.html", context)
    else:
        return render(request, 'login.html')

@login_required
def daily_registrations(request, date):
    if request.user.is_superuser:
        registrations = Registration.objects.filter(registered_on=date)
        return render(request, 'daily_registrations.html', {'registrations': registrations})
    else:
        return redirect('login')
from django.shortcuts import render
from .models import Registration
from datetime import datetime

import csv
from django.http import HttpResponse

@login_required
def logout_me(request):
    logout(request)
    return redirect('login')

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(username, password)
        # Check if the username and password match any user
        user = head.objects.filter(username=username, password=password)
        print(user)
        if len(user) > 0:
            print(user)
            # A backend authenticated the credentials
            login(request, user.first())
            return redirect('dashboard')
        else:
            # Invalid credentials
            try:
                user = head.objects.get(username=username)
                if user.check_password(password):
                    login(request, user)
                    return redirect('dashboard')
            except head.DoesNotExist:
                messages.error(request, "Invalid username or password.")
    return render(request, 'login.html')
@login_required
def registration_list(request):
    if request.user.is_superuser:
    # Get the search parameters
        search_date = request.GET.get('search_date')
        print(search_date)
        category_id = request.GET.get('category')  # Get the category from the query parameters
        if search_date == '':
            search_date = None
        # Retrieve all registrations by default
        registrations = Registration.objects.all()

        # Filter registrations by date if provided
        if search_date:
            try:
                date_object = datetime.strptime(search_date, '%Y-%m-%d').date()
                registrations = registrations.filter(registered_on=date_object)
            except ValueError:
                pass

        # Filter registrations by category if provided
        if category_id:
            registrations = registrations.filter(event__category_id=category_id)

        # Handle CSV download
        if "download" in request.GET:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="registrations.csv"'

            writer = csv.writer(response)
            writer.writerow(['Name', 'Roll Number', 'Year', 'Branch', 'Section', 'Email', 'Mobile Number', 'Event', 'Date'])
            for reg in registrations:
                writer.writerow([
                    reg.name, reg.roll_number, reg.year, reg.branch, reg.section,
                    reg.email, reg.mobile_number, reg.event.name, reg.registered_on
                ])
            return response

        # Retrieve all categories for the filter dropdown
        categories = Category.objects.all()

        context = {
            'registrations': registrations,
            'search_date': search_date,
            'categories': categories,
            'selected_category': category_id,
        }
        return render(request, 'registrations.html', context)
    else:
        return redirect('login')
@login_required
def dashboard(request):
    head_of = request.user.category
    registrations = Registration.objects.filter(event__category=head_of)
    event_count = {}
    for reg in registrations:
        if reg.event.name in event_count:
            event_count[reg.event.name] += 1
        else:
            event_count[reg.event.name] = 1
    count = len(registrations)
    context = {
        'registrations': registrations,
        'total': count,
        'event_count': event_count
        }
    return render(request, 'dashboard.html', context)

import openpyxl
from django.http import HttpResponse
from .models import Registration
@login_required
def export_to_excel(request, date):
    if request.user.is_superuser:
        registrations = Registration.objects.filter(registered_on=date)
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = f"Registrations {date}"

        # Header row
        headers = ['Name', 'Roll Number', 'Year', 'Branch', 'Section', 'Email', 'Mobile Number', 'Event']
        sheet.append(headers)

        # Data rows
        for reg in registrations:
            sheet.append([
                reg.name, reg.roll_number, reg.year, reg.branch, reg.section,
                reg.email, reg.mobile_number, reg.event.name
            ])

        # Response
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Registrations_{date}.xlsx"'
        workbook.save(response)
        return response
    else:
        return HttpResponse("Unauthorized", status=401)
from django.shortcuts import render
from django.db.models import Count, F, Sum
from .models import Category

def admin_dashboard(request):
    categories = Category.objects.prefetch_related("events").all()
    
    category_data = []
    grand_total_registrations = 0
    grand_total_amount = 0

    for category in categories:
        events = category.events.annotate(
            registration_count=Count("registration"),
            total_price=F("price") * Count("registration")
        )

        total_category_registrations = sum(event.registration_count for event in events)
        total_category_amount = sum(event.total_price for event in events)

        grand_total_registrations += total_category_registrations
        grand_total_amount += total_category_amount

        category_data.append({
            "category": category.name,
            "events": events,
            "total_registrations": total_category_registrations,
            "total_amount": total_category_amount
        })

    return render(request, "admin_dashboard.html", {
        "category_data": category_data,
        "grand_total_registrations": grand_total_registrations,
        "grand_total_amount": grand_total_amount
    })
