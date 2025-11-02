from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from .models import Review, Commentaire
from .forms import ReviewForm, CommentaireForm


def reviews_list(request):
    """
    Display list of all approved reviews
    User Story 8.6 - Filter reviews
    User Story 8.4 - Search reviews
    """
    reviews = Review.objects.filter(is_approved=True).select_related('user', 'car')
    
    # Search functionality (8.4)
    search_query = request.GET.get('q', '')
    if search_query:
        reviews = reviews.filter(
            Q(titre__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Filter by rating (8.6)
    min_note = request.GET.get('min_note')
    max_note = request.GET.get('max_note')
    if min_note:
        reviews = reviews.filter(note__gte=min_note)
    if max_note:
        reviews = reviews.filter(note__lte=max_note)
    
    # Filter by car (8.6)
    car_id = request.GET.get('car')
    if car_id:
        reviews = reviews.filter(car_id=car_id)
    
    # Sort options (8.5)
    sort_by = request.GET.get('sort', '-date_review')
    allowed_sorts = ['-date_review', 'date_review', '-note', 'note']
    if sort_by in allowed_sorts:
        reviews = reviews.order_by(sort_by)
    
    # Add comment count annotation
    reviews = reviews.annotate(comment_count=Count('commentaires'))
    
    # Pagination
    paginator = Paginator(reviews, 12)  # 12 reviews per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate average rating
    avg_rating = Review.objects.filter(is_approved=True).aggregate(Avg('note'))['note__avg']
    
    context = {
        'title': 'Car Dealer Reviews',
        'page_obj': page_obj,
        'search_query': search_query,
        'avg_rating': round(avg_rating, 1) if avg_rating else 0,
        'total_reviews': reviews.count(),
    }
    
    return render(request, 'reviews/reviews_list.html', context)


def review_detail(request, pk):
    """
    Display a single review with its comments
    User Story 9.1 - Add comment form here
    """
    review = get_object_or_404(
        Review.objects.select_related('user', 'car'),
        pk=pk,
        is_approved=True
    )
    
    # Get approved comments
    commentaires = review.commentaires.filter(
        is_approved=True
    ).select_related('user').order_by('date_commentaire')
    
    # Comment form
    comment_form = CommentaireForm()
    
    # Handle comment submission (9.1)
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentaireForm(request.POST)
        if comment_form.is_valid():
            commentaire = comment_form.save(commit=False)
            commentaire.user = request.user
            commentaire.review = review
            commentaire.save()
            messages.success(request, 'Votre commentaire a été ajouté avec succès!')
            return redirect('reviews:detail', pk=pk)
    
    context = {
        'title': f'{review.titre} - Review',
        'review': review,
        'commentaires': commentaires,
        'comment_form': comment_form,
    }
    
    return render(request, 'reviews/review_detail.html', context)


@login_required
def add_review(request, car_id=None):
    """
    Add a new review (User Story 8.1 - Must have)
    """
    # Check if car_id provided and user hasn't already reviewed this car
    if car_id:
        # Note: Update this when you have the Car model
        # car = get_object_or_404(Car, pk=car_id)
        # if Review.objects.filter(user=request.user, car=car).exists():
        #     messages.warning(request, 'Vous avez déjà posté un avis pour cette voiture.')
        #     return redirect('car_detail', pk=car_id)
        pass
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            # if car_id:
            #     review.car = car
            review.save()
            messages.success(request, 'Votre avis a été ajouté avec succès!')
            return redirect('reviews:detail', pk=review.pk)
    else:
        form = ReviewForm()
    
    context = {
        'title': 'Ajouter un avis',
        'form': form,
        # 'car': car if car_id else None,
    }
    
    return render(request, 'reviews/add_review.html', context)


@login_required
def edit_review(request, pk):
    """
    Edit existing review (User Story 8.2 - Should have)
    Only the review author can edit
    """
    review = get_object_or_404(Review, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre avis a été modifié avec succès!')
            return redirect('reviews:detail', pk=pk)
    else:
        form = ReviewForm(instance=review)
    
    context = {
        'title': 'Modifier l\'avis',
        'form': form,
        'review': review,
    }
    
    return render(request, 'reviews/edit_review.html', context)


@login_required
def delete_review(request, pk):
    """
    Delete review (User Story 8.3 - Could have)
    Only the review author can delete
    """
    review = get_object_or_404(Review, pk=pk, user=request.user)
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Votre avis a été supprimé.')
        return redirect('reviews:list')
    
    context = {
        'title': 'Supprimer l\'avis',
        'review': review,
    }
    
    return render(request, 'reviews/delete_review.html', context)


@login_required
def my_reviews(request):
    """
    Display current user's reviews
    """
    reviews = Review.objects.filter(user=request.user).order_by('-date_review')
    
    context = {
        'title': 'Mes avis',
        'reviews': reviews,
    }
    
    return render(request, 'reviews/my_reviews.html', context)


@login_required
def edit_comment(request, pk):
    """
    Edit comment (User Story 9.2 - Could have)
    """
    commentaire = get_object_or_404(Commentaire, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = CommentaireForm(request.POST, instance=commentaire)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre commentaire a été modifié!')
            return redirect('reviews:detail', pk=commentaire.review.pk)
    else:
        form = CommentaireForm(instance=commentaire)
    
    context = {
        'title': 'Modifier le commentaire',
        'form': form,
        'commentaire': commentaire,
    }
    
    return render(request, 'reviews/edit_comment.html', context)


@login_required
def delete_comment(request, pk):
    """
    Delete comment (User Story 9.3 - Could have)
    """
    commentaire = get_object_or_404(Commentaire, pk=pk, user=request.user)
    review_pk = commentaire.review.pk
    
    if request.method == 'POST':
        commentaire.delete()
        messages.success(request, 'Votre commentaire a été supprimé.')
        return redirect('reviews:detail', pk=review_pk)
    
    context = {
        'title': 'Supprimer le commentaire',
        'commentaire': commentaire,
    }
    
    return render(request, 'reviews/delete_comment.html', context)