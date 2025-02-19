from datetime import datetime, timedelta

from django.db.models import Count, F
from django.utils.timezone import make_aware
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order
from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer,
    MovieSerializer,
    MovieSessionSerializer,
    MovieDetailSerializer,
    MovieSessionDetailSerializer,
    MovieListSerializer,
    OrderSerializer,
    OrderListSerializer,
    MovieSessionAdvancedListSerializer,
)
from cinema_service.pagination import OrderPagination


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class CinemaHallViewSet(viewsets.ModelViewSet):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer
        if self.action == "retrieve":
            return MovieDetailSerializer
        return MovieSerializer

    def get_queryset(self):
        queryset = Movie.objects.all().prefetch_related("actors", "genres")

        actors = self.request.GET.get("actors")
        genres = self.request.GET.get("genres")
        title = self.request.GET.get("title")

        if actors:
            actors_ids = [int(actor_id) for actor_id in actors.split(",")]
            queryset = queryset.filter(
                actors__id__in=actors_ids).order_by("actors")

        if genres:
            genres_ids = [int(genre_id) for genre_id in genres.split(",")]
            queryset = queryset.filter(
                genres__id__in=genres_ids).order_by("genres")

        if title:
            queryset = queryset.filter(title__icontains=title)

        return queryset.distinct()


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = MovieSession.objects.all()
    serializer_class = MovieSessionSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return MovieSessionAdvancedListSerializer
        if self.action == "retrieve":
            return MovieSessionDetailSerializer
        return MovieSessionSerializer

    def get_queryset(self):
        queryset = MovieSession.objects.all().prefetch_related(
            "movie",
            "cinema_hall"
        )

        date = self.request.GET.get("date")
        movies = self.request.GET.get("movie")

        if self.action == "list":
            queryset = (
                queryset
                .annotate(
                    tickets_available=(
                        F("cinema_hall__rows")
                        * F("cinema_hall__seats_in_row")
                        - Count("tickets"))
                )
            )

        if date:
            try:
                start_date = datetime.strptime(date, "%Y-%m-%d")
                start_date = make_aware(datetime.combine(
                    start_date, datetime.min.time()))
                end_date = start_date + timedelta(days=1)
                queryset = queryset.filter(
                    show_time__gte=start_date,
                    show_time__lt=end_date,
                )
            except ValueError:
                raise ValidationError("Invalid date format. Use YYYY-MM-DD")

        if movies:
            movie_ids = [int(movie) for movie in movies.split(",")]
            queryset = queryset.filter(movie_id__in=movie_ids)

        return queryset.distinct()


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user)
        return queryset.select_related("user").prefetch_related(
            "tickets__movie_session__cinema_hall",
            "tickets__movie_session__movie",
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        elif self.action == "retrieve":
            return OrderSerializer
        else:
            return OrderSerializer
