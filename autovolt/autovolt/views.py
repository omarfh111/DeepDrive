from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

def indexMain(request):
    context= {
            'title': 'Car Dealer Django Template',
    }
    return render(request, 'index.html', context)

def indexTwo(request):
    context= {
            'title': 'Car Dealer Django Template',
    }
    return render(request, 'index-two.html', context)

def indexThree(request):
    context= {
            'title': 'Car Dealer Django Template',
    }
    return render(request, 'index-three.html', context)

def indexFour(request):
    context= {
            'title': 'Car Dealer Django Template',
    }
    return render(request, 'index-four.html', context)

def indexFive(request):
    context= {
            'title': 'Car Dealer Django Template',
    }
    return render(request, 'index-five.html', context)

def indexSix(request):
    context= {
            'title': 'Car Dealer Django Template',
    }
    return render(request, 'index-six.html', context)

def indexSeven(request):
    context= {
            'title': 'Car Dealer Django Template',
    }
    return render(request, 'index-seven.html', context)

def indexEight(request):
    context= {
            'title': 'Car Dealer Django Template',
    }
    return render(request, 'index-eight.html', context)

def About(request):
    context= {
            'title': 'Car Dealer About Us',
    }
    return render(request, 'about.html', context)

# car page
def portfolio(request):
    context= {
            'title': 'Car Dealer Portfolio Page',
    }
    return render(request, 'portfolio.html', context)

def portfolioTwo(request):
    context= {
            'title': 'Car Dealer Portfolio Two',
    }
    return render(request, 'portfolio-2.html', context)

def portfolioThree(request):
    context= {
            'title': 'Car Dealer Portfolio Three',
    }
    return render(request, 'portfolio-3.html', context)

def portfolioDetails(request):
    context= {
            'title': 'Car Dealer Portfolio Details',
    }
    return render(request, 'portfolio-details.html', context)

def portfolioDetailsTwo(request):
    context= {
            'title': 'Car Dealer Portfolio Details',
    }
    return render(request, 'portfolio-details-2.html', context)

def service(request):
    context= {
            'title': 'Car Dealer Service Page',
    }
    return render(request, 'service.html', context)

def pricing(request):
    context= {
            'title': 'Car Dealer Pricing Page',
    }
    return render(request, 'pricing.html', context)

def faq(request):
    context= {
            'title': 'Car Dealer FAQ Page',
    }
    return render(request, 'faq.html', context)

def soldCar(request):
    context= {
            'title': 'Car Dealer Sold Car',
    }
    return render(request, 'sold-car.html', context)

def calculator(request):
    context= {
            'title': 'Car Dealer Calculator',
    }
    return render(request, 'calculator.html', context)

def account(request):
    """
    Account page with login and registration forms
    """
    context = {
        'title': 'Car Dealer Account',
    }
    
    # Initialize registration form
    registration_form = UserCreationForm()
    
    # Handle login
    if request.method == 'POST' and 'login' in request.POST:
        username = request.POST.get('email')  # Form uses 'email' field name for username
        password = request.POST.get('password')
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'You have been logged in successfully!')
                return redirect('index')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please provide both username and password.')
    
    # Handle registration
    elif request.method == 'POST' and 'register' in request.POST:
        registration_form = UserCreationForm(request.POST)
        if registration_form.is_valid():
            user = registration_form.save()
            username = registration_form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            # Auto-login after registration
            login(request, user)
            return redirect('index')
    
    context['registration_form'] = registration_form
    return render(request, 'account.html', context)

def blog(request):
    context= {
            'title': 'Car Dealer Blog',
    }
    return render(request, 'blog.html', context)

def blogTwo(request):
    context= {
            'title': 'Car Dealer Blog Two',
    }
    return render(request, 'blog-2.html', context)

def blogDetails(request):
    context= {
            'title': 'Car Dealer Blog Details',
    }
    return render(request, 'blog-details.html', context)

def team(request):
    context= {
            'title': 'Car Dealer Team Page',
    }
    return render(request, 'team.html', context)

def carDealer(request):
    context= {
            'title': 'Car Dealer Page',
    }
    return render(request, 'car-dealer.html', context)

def carDealerDetails(request):
    context= {
            'title': 'Car Dealer Details Page',
    }
    return render(request, 'car-dealer-details.html', context)

def shop(request):
    context= {
            'title': 'Car Dealer Shop Page',
    }
    return render(request, 'shop.html', context)

def shopTwo(request):
    context= {
            'title': 'Car Dealer Shop Two Page',
    }
    return render(request, 'shop-2.html', context)

def shopThree(request):
    context= {
            'title': 'Car Dealer Shop Three Page',
    }
    return render(request, 'shop-3.html', context)

def cart(request):
    context= {
            'title': 'Car Dealer Cart Page',
    }
    return render(request, 'cart.html', context)

def checkout(request):
        context= {
                'title': 'Car Dealer Checkout Page',
        }
        return render(request, 'checkout.html', context)

def shopDetails(request):
    context= {
            'title': 'Car Dealer Shop Details Page',
    }
    return render(request, 'shop-details.html', context)

def contact(request):
    context= {
            'title': 'Car Dealer Contact Page',
    }
    return render(request, 'contact.html', context)

