import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from chat.models import Room, Message

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demo data: 10 rooms and 20 users with conversations'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')

        # Create 20 users
        usernames = [
            'alice', 'bob', 'charlie', 'dave', 'eve', 'frank', 'grace', 'henry',
            'iris', 'jack', 'kate', 'liam', 'mike', 'nora', 'oscar', 'paul',
            'quinn', 'rose', 'sam', 'tina'
        ]

        users = []
        for username in usernames:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@demo.com',
                    'is_online': random.choice([True, False]),
                }
            )
            if created:
                user.set_password('demo123')
                # Set random last seen for offline users
                if not user.is_online:
                    minutes_ago = random.randint(1, 1440)  # 1 min to 24 hours ago
                    user.last_seen = timezone.now() - timedelta(minutes=minutes_ago)
                user.save()
                self.stdout.write(f'  Created user: {username}')
            else:
                self.stdout.write(f'  User exists: {username}')
            users.append(user)

        # Create 10 rooms
        room_data = [
            {'name': 'General', 'description': 'General discussion for everyone', 'is_private': False},
            {'name': 'Tech Talk', 'description': 'Technology and programming', 'is_private': False},
            {'name': 'Random', 'description': 'Random conversations', 'is_private': False},
            {'name': 'Music', 'description': 'Share your favorite tunes', 'is_private': False},
            {'name': 'Movies', 'description': 'Film and TV discussions', 'is_private': False},
            {'name': 'Developers', 'description': 'Private dev team room', 'is_private': True},
            {'name': 'Design Team', 'description': 'Design discussions', 'is_private': True},
            {'name': 'Project Alpha', 'description': 'Secret project room', 'is_private': True},
            {'name': 'Friends', 'description': 'Close friends only', 'is_private': True},
            {'name': 'Gaming', 'description': 'Game night planning', 'is_private': False},
        ]

        rooms = []
        for data in room_data:
            room, created = Room.objects.get_or_create(
                name=data['name'],
                defaults={
                    'slug': data['name'].lower().replace(' ', '-'),
                    'description': data['description'],
                    'is_private': data['is_private'],
                    'admin': random.choice(users),
                }
            )
            if created:
                self.stdout.write(f'  Created room: {data["name"]}')
            else:
                self.stdout.write(f'  Room exists: {data["name"]}')

            # Add random members to private rooms
            if data['is_private']:
                member_count = random.randint(3, 8)
                random_members = random.sample(users, member_count)
                room.members.add(*random_members)
            rooms.append(room)

        # Create sample conversations
        sample_messages = [
            "Hey everyone! How's it going?",
            "Just joined this room. Looks nice!",
            "Has anyone seen the latest update?",
            "I'm working on a new project, pretty excited about it.",
            "What do you all think about the new features?",
            "Good morning! ☀️",
            "Anyone up for a call later?",
            "Just finished my work for today 🎉",
            "Can someone help me with this bug?",
            "Thanks for the help everyone!",
            "This is amazing!",
            "lol that's funny 😂",
            "I'll be there in 5 minutes",
            "Did you see the news today?",
            "Let's plan something for the weekend",
            "I'm having coffee right now ☕",
            "Working from home today",
            "The weather is so nice today!",
            "Anyone want to grab lunch?",
            "Good night everyone! 🌙",
            "Just saw a great movie, highly recommend!",
            "Does anyone know a good restaurant nearby?",
            "I'm learning Django, it's pretty cool",
            "React or Vue? What do you prefer?",
            "Happy Friday! 🎊",
            "Monday blues... 😴",
            "Check out this link I found",
            "That's awesome!",
            "I agree with you",
            "Let me think about it",
            "Can you send me that file?",
            "Thanks!",
            "You're welcome!",
            "See you tomorrow",
            "Take care!",
            "Bye for now",
        ]

        # Generate messages for each room (50-150 messages per room)
        for room in rooms:
            message_count = random.randint(50, 150)
            self.stdout.write(f'  Creating {message_count} messages for {room.name}...')

            # Get users in this room (for private) or all users (for public)
            if room.is_private:
                room_users = list(room.members.all())
            else:
                room_users = users

            # Generate messages with timestamps going back
            base_time = timezone.now() - timedelta(days=random.randint(1, 7))

            for i in range(message_count):
                author = random.choice(room_users)
                content = random.choice(sample_messages)

                # Vary the timestamp
                timestamp = base_time + timedelta(minutes=i * random.randint(3, 30))

                Message.objects.create(
                    room=room,
                    author=author,
                    content=content,
                    timestamp=timestamp,
                    is_read=random.choice([True, False]),
                    is_edited=random.choice([True, False, False, False]),
                )

        # Create some direct message (DM) rooms between random users
        self.stdout.write('Creating DM conversations...')
        dm_pairs = [
            ('alice', 'bob'),
            ('charlie', 'dave'),
            ('eve', 'frank'),
            ('grace', 'henry'),
            ('iris', 'jack'),
        ]

        for username1, username2 in dm_pairs:
            try:
                user1 = User.objects.get(username=username1)
                user2 = User.objects.get(username=username2)
                dm_room = Room.get_or_create_private(user1, user2)
                self.stdout.write(f'  Created DM: {username1} & {username2}')

                # Add some messages to DM
                dm_messages = [
                    "Hey!",
                    "Hi there! How are you?",
                    "I'm good, thanks! What about you?",
                    "Doing great! Just wanted to check in.",
                    "That's nice. Any plans for the weekend?",
                    "Not sure yet, maybe catch a movie?",
                    "Sounds good! Let me know.",
                    "Will do. Talk later!",
                ]

                for i, content in enumerate(dm_messages):
                    author = user1 if i % 2 == 0 else user2
                    Message.objects.create(
                        room=dm_room,
                        author=author,
                        content=content,
                        timestamp=timezone.now() - timedelta(hours=len(dm_messages) - i),
                    )
            except User.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS('Demo data created successfully!'))
        self.stdout.write('')
        self.stdout.write('Login credentials for demo users:')
        self.stdout.write('  Username: any of ' + ', '.join(usernames[:5]) + ', ...')
        self.stdout.write('  Password: demo123')
