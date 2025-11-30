from django.http import JsonResponse
from django.contrib.auth.models import Group, User
from django.contrib.auth import logout, authenticate
from rest_framework import permissions, viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from api.serializers import GroupSerializer, UserSerializer, EmailLoginSerializer


def home(request):
    """
    View para a rota raiz '/'
    Retorna uma resposta JSON simples
    """
    return JsonResponse({
        'message': 'Bem-vindo à API do Simples Chat!',
        'status': 'success',
        'version': '1.0.0'
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def login_by_email(request):
    """
    View para login via email/password
    """
    serializer = EmailLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        try:
            # Busca o usuário pelo email
            user = User.objects.get(email=email)
            
            # Verifica se o usuário está ativo
            if not user.is_active:
                return Response({
                    'error': 'Conta desativada'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Autentica o usuário
            authenticated_user = authenticate(username=user.username, password=password)
            
            if authenticated_user is not None:
                # Cria ou obtém o token
                token, created = Token.objects.get_or_create(user=authenticated_user)
                
                return Response({
                    'token': token.key,
                    'user': {
                        'id': authenticated_user.id,
                        'username': authenticated_user.username,
                        'email': authenticated_user.email,
                        'first_name': authenticated_user.first_name,
                        'last_name': authenticated_user.last_name,
                        'is_staff': authenticated_user.is_staff,
                    }
                })
            else:
                return Response({
                    'error': 'Senha incorreta'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except User.DoesNotExist:
            return Response({
                'error': 'Usuário não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    View para logout via API
    """
    logout(request)
    return Response({'message': 'Logout realizado com sucesso'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    View para obter informações do usuário atual
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
        'date_joined': user.date_joined,
    })


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]