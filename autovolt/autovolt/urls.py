"""
URL configuration for autovolt project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from autovolt import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.indexMain, name='index'),
    path('index-two', views.indexTwo, name='index-two'),
    path('index-three', views.indexThree, name='index-three'),
    path('index-four', views.indexFour, name='index-four'),
    path('index-five', views.indexFive, name='index-five'),
    path('index-six', views.indexSix, name='index-six'),
    path('index-seven', views.indexSeven, name='index-seven'),
    path('index-eight', views.indexEight, name='index-eight'),
    path('about', views.About, name='about'),
    path('portfolio', views.portfolio, name='portfolio'),
    path('portfolio-2', views.portfolioTwo, name='portfolio-two'),
    path('portfolio-3', views.portfolioThree, name='portfolio-three'),
    path('portfolio-details', views.portfolioDetails, name='portfolio-details'),
    path('portfolio-details-2', views.portfolioDetailsTwo, name='portfolio-details-2'),
    path('service', views.service, name='service'),
    path('pricing', views.pricing, name='pricing'),
    path('faq', views.faq, name='faq'),
    path('sold-car', views.soldCar, name='sold-car'),
    path('calculator', views.calculator, name='calculator'),
    path('account', views.account, name='account'),
    path('blog', views.blog, name='blog'),
    path('blog-2', views.blogTwo, name='blog-2'),
    path('blog-details', views.blogDetails, name='blog-details'),
    path('team', views.team, name='team'),
    path('car-dealer', views.carDealer, name='car-dealer'),
    path('car-dealer-details', views.carDealerDetails, name='car-dealer-details'),
    path('shop', views.shop, name='shop'),
    path('shop-2', views.shopTwo, name='shop-2'),
    path('shop-3', views.shopThree, name='shop-3'),
    path('cart', views.cart, name='cart'),
    path('checkout', views.checkout, name='checkout'),
    path('shop-details', views.shopDetails, name='shop-details'),
    path('contact', views.contact, name='contact'),

]
