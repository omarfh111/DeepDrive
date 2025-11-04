from django.shortcuts import render, get_object_or_404, redirect
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

def update_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('portfolio')
    else:
        form = PostForm(instance=post)

    return render(request, 'update_post.html', {'form': form, 'post': post})

def delete_car(request, pk):
    car = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        car.delete()
        return redirect('portfolio')  # redirect to your main car list page
    return render(request, 'delete_car.html', {'car': Post})