from django.shortcuts import render
from .models import Post
from django.shortcuts import render, redirect
from .form import PostForm

def portfolio(request):
    posts = Post.objects.all()
    print(">>> Portfolio view executed, posts count:", posts.count())
    for p in posts:
        print("  -", p.marque, p.modele, p.image)
    return render(request, 'portfolio-2.html', {'posts': posts})

def add_car(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('portfolio')  # go back to the store page
    else:
        form = PostForm()
    return render(request, 'add_car.html', {'form': form})
