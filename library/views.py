from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer, AdditionalDaysSerializer
from rest_framework.decorators import action
from django.utils import timezone
from .tasks import send_loan_notification
from datetime import date, timedelta
from django.db.models import Count, Q

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related('author').all()
    serializer_class = BookSerializer

    def list(self, request, *args, **kwargs):
        book_qs = Book.objects.select_related('author').all()
        return Response(self.serializer(book_qs, many=True).data)

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

    @action(detail=False, methods=['GET'])
    def top_active(self, request):
        active_loans_qs = Loan.objects.select_related('member').annotate(
            total_active_loans = Count('loan', Q(is_returned = False))
        ).order_by('-total_active_loans')[:5]

        details_to_return = []
        for active_loan in active_loans_qs:
            details_to_return.append({
                'id': active_loan.member.id,
                'username': active_loan.member.user.get_full_name(),
                'active_loan': active_loan.total_active_loans
            })
        return Response(details_to_return, status=status.HTTP_200_OK)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    @action(detail=True, methods=['post'])
    def extend_due_date(self, request, pk=None):
        additional_days = AdditionalDaysSerializer(request.data)
        if not additional_days.is_valid():
            return Response({'error': 'Invalid  additional days.'}, status=status.HTTP_400_BAD_REQUEST)

        loan = self.get_object()

        if loan.due_date < date.today():
            return Response({'error': 'Your loan is not due to return nor extend.'}, status=status.HTTP_400_BAD_REQUEST)
        
        new_days = additional_days.validate_data('additional_days')
        loan.due_date += timedelta(days=int(new_days))
        loan.save()

        return Response({'data': additional_days.data}, status=status.HTTP_200_OK)