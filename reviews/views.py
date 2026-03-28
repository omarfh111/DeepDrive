from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Avg, Count, Case, When, FloatField  
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
    ✅ NEW: Added sentiment-based sorting
    """
    reviews = Review.objects.filter(is_approved=True).select_related('user')
    
    # Search functionality (8.4)
    search_query = request.GET.get('q', '')
    if search_query:
        reviews = reviews.filter(
            Q(titre__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Filter by rating (8.6)
    min_note = request.GET.get('min_note')
    max_note = request.GET.get('max_note')
    if min_note:
        reviews = reviews.filter(note__gte=min_note)
    if max_note:
        reviews = reviews.filter(note__lte=max_note)
    
    # ✅ UPDATED: Sort options with sentiment analysis
    sort_by = request.GET.get('sort', '-date_joined')
    
    # Handle sentiment-based sorting
    if sort_by == 'most_positive':
        # Sort by reviews with most positive sentiment
        reviews = reviews.annotate(
            positive_count=Count(
                'commentaires',
                filter=Q(commentaires__is_approved=True, 
                        commentaires__sentiment_label='Positive')
            ),
            negative_count=Count(
                'commentaires',
                filter=Q(commentaires__is_approved=True,
                        commentaires__sentiment_label='Negative')
            ),
            total_comments=Count(
                'commentaires',
                filter=Q(commentaires__is_approved=True)
            ),
            # Calculate positive ratio (percentage of positive comments)
            positive_ratio=Case(
                When(total_comments=0, then=0.0),
                default=1.0 * Count(
                    'commentaires',
                    filter=Q(commentaires__is_approved=True,
                            commentaires__sentiment_label='Positive')
                ) / Count(
                    'commentaires',
                    filter=Q(commentaires__is_approved=True)
                ),
                output_field=FloatField()
            )
        ).filter(total_comments__gt=0).order_by('-positive_ratio', '-positive_count')
        
    elif sort_by == 'most_negative':
        # Sort by reviews with most negative sentiment
        reviews = reviews.annotate(
            positive_count=Count(
                'commentaires',
                filter=Q(commentaires__is_approved=True,
                        commentaires__sentiment_label='Positive')
            ),
            negative_count=Count(
                'commentaires',
                filter=Q(commentaires__is_approved=True,
                        commentaires__sentiment_label='Negative')
            ),
            total_comments=Count(
                'commentaires',
                filter=Q(commentaires__is_approved=True)
            ),
            # Calculate negative ratio (percentage of negative comments)
            negative_ratio=Case(
                When(total_comments=0, then=0.0),
                default=1.0 * Count(
                    'commentaires',
                    filter=Q(commentaires__is_approved=True,
                            commentaires__sentiment_label='Negative')
                ) / Count(
                    'commentaires',
                    filter=Q(commentaires__is_approved=True)
                ),
                output_field=FloatField()
            )
        ).filter(total_comments__gt=0).order_by('-negative_ratio', '-negative_count')
    else:
        # Original sorting options
        allowed_sorts = ['-date_joined', 'date_joined', '-date_review', 'date_review', '-note', 'note']
        if sort_by in allowed_sorts:
            reviews = reviews.order_by(sort_by)
    
    # Add comment count annotation (if not already added by sentiment sorting)
    if sort_by not in ['most_positive', 'most_negative']:
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
    ✅ UPDATED: Auto-analyze sentiment when comment is added
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
    
    # ✅ UPDATED: Handle comment submission with sentiment analysis
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentaireForm(request.POST)
        if comment_form.is_valid():
            commentaire = comment_form.save(commit=False)
            commentaire.user = request.user
            commentaire.review = review
            commentaire.save()
            
            # ✅ NEW: Analyze sentiment immediately after saving
            try:
                commentaire.analyze_sentiment()
                messages.success(request, 'Votre commentaire a été ajouté avec succès!')
            except Exception as e:
                # Log the error but don't fail the comment creation
                messages.warning(request, 'Commentaire ajouté, mais l\'analyse de sentiment a échoué.')
                print(f"Sentiment analysis error: {e}")
            
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
            messages.success(request, 'Votre avis a été ajouté avec succès!')
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
def edit_comment_ajax(request, pk):
    """
    Edit comment via AJAX (User Story 9.2 - Could have)
    Only the comment author can edit
    Returns JSON response
    ✅ UPDATED: Re-analyze sentiment after edit
    """
    commentaire = get_object_or_404(Commentaire, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = CommentaireForm(request.POST, instance=commentaire)
        if form.is_valid():
            form.save()
            
            # ✅ NEW: Re-analyze sentiment after editing
            try:
                commentaire.analyze_sentiment()
            except Exception as e:
                print(f"Sentiment analysis error on edit: {e}")
            
            return JsonResponse({
                'success': True, 
                'message': 'Comment updated successfully',
                'commentaire': commentaire.commentaire,
                'review_pk': commentaire.review.pk
            })
        else:
            return JsonResponse({
                'success': False, 
                'message': 'Validation error',
                'errors': form.errors
            }, status=400)
    
    # GET request - return comment data for the form
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'commentaire': commentaire.commentaire
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


@login_required
def delete_comment_ajax(request, pk):
    """
    Delete comment via AJAX (User Story 9.3 - Could have)
    Only the comment author can delete
    Returns JSON response
    """
    if request.method == 'POST':
        commentaire = get_object_or_404(Commentaire, pk=pk, user=request.user)
        review_pk = commentaire.review.pk
        commentaire.delete()
        return JsonResponse({'success': True, 'message': 'Comment deleted successfully', 'review_pk': review_pk})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


# ==================== BACKOFFICE VIEWS (ADMIN ONLY) ====================

@user_passes_test(admin_required)
def backoffice_dashboard(request):
    """
    Backoffice dashboard showing overview of reviews and comments
    ✅ UPDATED: Added sentiment statistics
    """
    total_reviews = Review.objects.count()
    approved_reviews = Review.objects.filter(is_approved=True).count()
    pending_reviews = Review.objects.filter(is_approved=False).count()
    
    total_comments = Commentaire.objects.count()
    approved_comments = Commentaire.objects.filter(is_approved=True).count()
    pending_comments = Commentaire.objects.filter(is_approved=False).count()
    
    # ✅ NEW: Add sentiment statistics
    positive_comments = Commentaire.objects.filter(
        is_approved=True,
        sentiment_label='Positive'
    ).count()
    negative_comments = Commentaire.objects.filter(
        is_approved=True,
        sentiment_label='Negative'
    ).count()
    neutral_comments = Commentaire.objects.filter(
        is_approved=True,
        sentiment_label='Neutral'
    ).count()
    
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
        'positive_comments': positive_comments,  # ✅ NEW
        'negative_comments': negative_comments,  # ✅ NEW
        'neutral_comments': neutral_comments,    # ✅ NEW
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
            messages.success(request, f'Review {"approuvé" if review.is_approved else "désapprouvé"}!')
            return redirect('reviews:backoffice_review_detail', pk=pk)
        
        # Handle delete
        if 'delete' in request.POST:
            review.delete()
            messages.success(request, 'Review supprimé avec succès!')
            return redirect('reviews:reviews_backreviews_list')
        
        # Handle edit
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Review modifié avec succès!')
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
    ✅ UPDATED: Re-analyze sentiment after admin edit
    """
    commentaire = get_object_or_404(Commentaire.objects.select_related('user', 'review'), pk=pk)
    
    if request.method == 'POST':
        # Handle approval toggle
        if 'toggle_approval' in request.POST:
            commentaire.is_approved = not commentaire.is_approved
            commentaire.save()
            messages.success(request, f'Commentaire {"approuvé" if commentaire.is_approved else "désapprouvé"}!')
            return redirect('reviews:backoffice_commentaire_detail', pk=pk)
        
        # Handle delete
        if 'delete' in request.POST:
            commentaire.delete()
            messages.success(request, 'Commentaire supprimé avec succès!')
            return redirect('reviews:reviews_commentaires_list')
        
        # Handle edit
        form = CommentaireForm(request.POST, instance=commentaire)
        if form.is_valid():
            form.save()
            
            # ✅ NEW: Re-analyze sentiment after admin edit
            try:
                commentaire.analyze_sentiment()
            except Exception as e:
                print(f"Sentiment analysis error on admin edit: {e}")
            
            messages.success(request, 'Commentaire modifié avec succès!')
            return redirect('reviews:backoffice_commentaire_detail', pk=pk)
    else:
        form = CommentaireForm(instance=commentaire)
    
    context = {
        'commentaire': commentaire,
        'form': form,
    }
    
    return render(request, 'reviews/commentaire_detail.html', context)


# ✅ NEW: Optional admin action to re-analyze all sentiments
@user_passes_test(admin_required)
def reanalyze_all_sentiments(request):
    """
    Admin view to trigger re-analysis of all comment sentiments
    """
    if request.method == 'POST':
        from .models import Commentaire
        
        comments = Commentaire.objects.filter(is_approved=True)
        total = comments.count()
        success_count = 0
        error_count = 0
        
        for comment in comments:
            try:
                comment.analyze_sentiment()
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"Error analyzing comment {comment.id}: {e}")
        
        messages.success(
            request,
            f'Sentiment analysis complete! {success_count} succès, {error_count} erreurs sur {total} commentaires.'
        )
        return redirect('reviews:backoffice_dashboard')
    
    # GET request - show confirmation page
    total_comments = Commentaire.objects.filter(is_approved=True).count()
    
    context = {
        'total_comments': total_comments,
    }
    
    return render(request, 'reviews/reanalyze_sentiments.html', context)