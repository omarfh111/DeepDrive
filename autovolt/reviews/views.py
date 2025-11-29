from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Review, Commentaire
from .forms import ReviewForm, CommentaireForm


def admin_required(user):
    """Check if user is staff (admin)"""
    return user.is_authenticated and user.is_staff


def reviews_list(request):
    """
    Display list of all approved reviews
    User Story 8.6 - Filter reviews
    User Story 8.4 - Search reviews
    """
    reviews = Review.objects.filter(is_approved=True).select_related('user')
    
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
    
    # Sort options (8.5)
    sort_by = request.GET.get('sort', '-date_joined')
    allowed_sorts = ['-date_joined', 'date_joined', '-date_review', 'date_review', '-note', 'note']
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
        'title': 'Reviews',
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
        Review.objects.select_related('user'),
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
            return redirect('reviews:detail', pk=pk)
    
    context = {
        'title': f'{review.titre} - Review',
        'review': review,
        'commentaires': commentaires,
        'comment_form': comment_form,
    }
    
    return render(request, 'reviews/review_detail.html', context)


@login_required
def add_review(request):
    """
    Add a new review (User Story 8.1 - Must have)
    """
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.save()
            return redirect('reviews:detail', pk=review.pk)
    else:
        form = ReviewForm()
    
    context = {
        'title': 'Ajouter un avis',
        'form': form,
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
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            form.save()
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
def delete_review_ajax(request, pk):
    """
    Delete review via AJAX (User Story 8.3 - Could have)
    Only the review author can delete
    Returns JSON response
    """
    if request.method == 'POST':
        review = get_object_or_404(Review, pk=pk, user=request.user)
        review.delete()
        return JsonResponse({'success': True, 'message': 'Review deleted successfully'})

    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
def my_reviews(request):
    """
    Display current user's reviews
    """
    reviews = Review.objects.filter(user=request.user).order_by('-date_joined')
    
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
        return redirect('reviews:detail', pk=review_pk)
    
    context = {
        'title': 'Supprimer le commentaire',
        'commentaire': commentaire,
    }
    
    return render(request, 'reviews/delete_comment.html', context)


# ==================== BACKOFFICE VIEWS (ADMIN ONLY) ====================

@user_passes_test(admin_required)
def backoffice_dashboard(request):
    """
    Backoffice dashboard showing overview of reviews and comments
    """
    total_reviews = Review.objects.count()
    approved_reviews = Review.objects.filter(is_approved=True).count()
    pending_reviews = Review.objects.filter(is_approved=False).count()
    
    total_comments = Commentaire.objects.count()
    approved_comments = Commentaire.objects.filter(is_approved=True).count()
    pending_comments = Commentaire.objects.filter(is_approved=False).count()
    
    avg_rating = Review.objects.filter(is_approved=True).aggregate(Avg('note'))['note__avg'] or 0
    
    recent_reviews = Review.objects.select_related('user').order_by('-date_joined')[:5]
    recent_comments = Commentaire.objects.select_related('user', 'review').order_by('-date_commentaire')[:5]
    
    context = {
        'total_reviews': total_reviews,
        'approved_reviews': approved_reviews,
        'pending_reviews': pending_reviews,
        'total_comments': total_comments,
        'approved_comments': approved_comments,
        'pending_comments': pending_comments,
        'avg_rating': round(avg_rating, 2),
        'recent_reviews': recent_reviews,
        'recent_comments': recent_comments,
    }
    
    return render(request, 'reviews/dashboard.html', context)


@user_passes_test(admin_required)
def backoffice_reviews_list(request):
    """
    Backoffice view to list all reviews with DataTables
    """
    reviews = Review.objects.select_related('user').prefetch_related('commentaires').all()
    
    context = {
        'reviews': reviews,
    }
    
    return render(request, 'reviews/backreviews_list.html', context)


@user_passes_test(admin_required)
def backoffice_review_detail(request, pk):
    """
    Backoffice view to view/edit a single review
    """
    review = get_object_or_404(Review.objects.select_related('user'), pk=pk)
    
    if request.method == 'POST':
        # Handle approval toggle
        if 'toggle_approval' in request.POST:
            review.is_approved = not review.is_approved
            review.save()
            return redirect('reviews:backoffice_review_detail', pk=pk)
        
        # Handle delete
        if 'delete' in request.POST:
            review.delete()
            return redirect('reviews:reviews_backreviews_list')
        
        # Handle edit
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            form.save()
            return redirect('reviews:backoffice_review_detail', pk=pk)
    else:
        form = ReviewForm(instance=review)
    
    commentaires = review.commentaires.select_related('user').all()
    
    context = {
        'review': review,
        'form': form,
        'commentaires': commentaires,
    }
    
    return render(request, 'reviews/backreview_detail.html', context)


@user_passes_test(admin_required)
def backoffice_commentaires_list(request):
    """
    Backoffice view to list all commentaires with DataTables
    """
    commentaires = Commentaire.objects.select_related('user', 'review').all()
    
    context = {
        'commentaires': commentaires,
    }
    
    return render(request, 'reviews/commentaires_list.html', context)


@user_passes_test(admin_required)
def backoffice_commentaire_detail(request, pk):
    """
    Backoffice view to view/edit a single commentaire
    """
    commentaire = get_object_or_404(Commentaire.objects.select_related('user', 'review'), pk=pk)
    
    if request.method == 'POST':
        # Handle approval toggle
        if 'toggle_approval' in request.POST:
            commentaire.is_approved = not commentaire.is_approved
            commentaire.save()
            return redirect('reviews:backoffice_commentaire_detail', pk=pk)
        
        # Handle delete
        if 'delete' in request.POST:
            commentaire.delete()
            return redirect('reviews:reviews_commentaires_list')
        
        # Handle edit
        form = CommentaireForm(request.POST, instance=commentaire)
        if form.is_valid():
            form.save()
            return redirect('reviews:backoffice_commentaire_detail', pk=pk)
    else:
        form = CommentaireForm(instance=commentaire)
    
    context = {
        'commentaire': commentaire,
        'form': form,
    }
    
    return render(request, 'reviews/commentaire_detail.html', context)