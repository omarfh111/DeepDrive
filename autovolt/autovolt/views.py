from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied











User = get_user_model()

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
    context= {
            'title': 'Car Dealer Account',
    }
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



class RoleAwareLoginView(LoginView):
    template_name = "auth/login.html"

    def get_success_url(self):
        nxt = self.get_redirect_url()
        if nxt:
            return nxt
        user = self.request.user
        if user.is_staff and getattr(user, "role", "") == "admin":
            return reverse("back_users")
        return reverse("home")


def _is_admin_and_staff(u):
    if not u.is_authenticated:
        return False
    if getattr(u, "role", "") == "admin" and u.is_staff:
        return True
    raise PermissionDenied

@login_required(login_url="login")
@user_passes_test(_is_admin_and_staff, login_url="login")
def back_users(request):
    if not (request.user.is_staff and getattr(request.user, "role", "") == "admin"):
        raise PermissionDenied
    return render(request, "user_app/admin_user_list.html")