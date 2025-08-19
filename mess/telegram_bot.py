"""
Telegram Bot implementation for Mess Management System
Handles all bot interactions and commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from django.conf import settings
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from asgiref.sync import sync_to_async
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from .models import Student, Payment, MessCut, StudentStatus, PaymentStatus
from core.utils import generate_qr_code, parse_telegram_date, is_within_cutoff_time
from .tasks import send_telegram_notification, sync_to_google_sheets

logger = logging.getLogger(__name__)


class TelegramBot:
    """Main Telegram bot handler"""
    
    def __init__(self):
        """Initialize bot with token"""
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.admin_ids = settings.ADMIN_TG_IDS
        self.application = Application.builder().token(self.token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup command and message handlers"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("register", self.register_command))
        self.application.add_handler(CommandHandler("payment", self.payment_command))
        self.application.add_handler(CommandHandler("messcut", self.messcut_command))
        self.application.add_handler(CommandHandler("myqr", self.myqr_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Admin commands
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        
        # Callback queries
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user = update.effective_user
        
        keyboard = [
            [InlineKeyboardButton("📝 Register", callback_data='register')],
            [InlineKeyboardButton("💳 Upload Payment", callback_data='payment')],
            [InlineKeyboardButton("✂️ Take Mess Cut", callback_data='messcut')],
            [InlineKeyboardButton("🎫 My QR", callback_data='myqr')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        
        if user.id in self.admin_ids:
            keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data='admin')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
Welcome to Mess Management System, {user.first_name}! 👋

I'm here to help you manage your mess operations. Use the buttons below to:

• Register for mess access
• Upload payment screenshots  
• Apply for mess cuts
• View your QR code
• Get help and support

Please select an option to continue:
        """
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context):
        """Handle /help command"""
        help_text = """
📚 **Mess Management Help**

**Available Commands:**
/start - Main menu
/register - New registration
/payment - Upload payment
/messcut - Apply for mess cut
/myqr - View your QR code
/status - Check your status
/help - This help message

**Important Notes:**
⏰ Mess cut deadline: 11:00 PM for next day
📸 Payment screenshots must be clear
🎫 Keep your QR code safe and don't share

**Support:**
Contact @mess_support for assistance
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

    # Callback handlers for inline buttons
    async def register_callback(self, update: Update, context):
        """Handle register button callback"""
        query = update.callback_query
        user = update.effective_user

        # Check if already registered
        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            await query.edit_message_text(
                f"You're already registered with status: {student.status}"
            )
            return
        except Student.DoesNotExist:
            pass

        # Start registration flow
        context.user_data['registration_flow'] = {'step': 'name'}
        await query.edit_message_text(
            "Let's start your registration!\n\nPlease enter your full name:"
        )

    async def payment_callback(self, update: Update, context):
        """Handle payment button callback"""
        query = update.callback_query
        user = update.effective_user

        # Check if registered and approved
        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            if student.status != StudentStatus.APPROVED:
                await query.edit_message_text(
                    "Your registration is not approved yet. Please wait for admin approval."
                )
                return
        except Student.DoesNotExist:
            await query.edit_message_text(
                "Please register first using /register"
            )
            return

        # Start payment flow
        context.user_data['payment_flow'] = {
            'step': 'cycle_start',
            'student_id': student.id
        }
        await query.edit_message_text(
            "💳 Payment Upload\n\nPlease enter the cycle start date (YYYY-MM-DD):"
        )

    async def messcut_callback(self, update: Update, context):
        """Handle mess cut button callback"""
        query = update.callback_query
        user = update.effective_user

        # Check if registered and approved
        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            if student.status != StudentStatus.APPROVED:
                await query.edit_message_text(
                    "Your registration is not approved yet."
                )
                return
        except Student.DoesNotExist:
            await query.edit_message_text(
                "Please register first using /register"
            )
            return

        # Start mess cut flow
        context.user_data['messcut_flow'] = {
            'step': 'from_date',
            'student_id': student.id
        }
        await query.edit_message_text(
            "✂️ Mess Cut Application\n\nPlease enter the start date (YYYY-MM-DD):"
        )

    async def myqr_callback(self, update: Update, context):
        """Handle QR code button callback"""
        query = update.callback_query
        user = update.effective_user

        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            if student.status != StudentStatus.APPROVED:
                await query.edit_message_text(
                    "Your registration is not approved yet."
                )
                return

            # Generate QR code
            qr_data = f"{student.roll_no}:{student.qr_nonce}:{student.qr_version}"
            qr_code_url = generate_qr_code(qr_data)

            await query.edit_message_text(
                f"🎫 Your QR Code\n\nRoll No: {student.roll_no}\nName: {student.name}\n\nShow this QR code at the mess counter:"
            )

            # Send QR code image
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=qr_code_url,
                caption=f"QR Code for {student.name} ({student.roll_no})"
            )

        except Student.DoesNotExist:
            await query.edit_message_text(
                "Please register first using /register"
            )

    async def help_callback(self, update: Update, context):
        """Handle help button callback"""
        query = update.callback_query

        help_text = """
🆘 **Help & Support**

**Available Commands:**
• `/start` - Main menu
• `/register` - Register for mess
• `/payment` - Upload payment screenshot
• `/messcut` - Apply for mess cut
• `/myqr` - View your QR code
• `/status` - Check your status
• `/help` - Show this help

**Need Help?**
Contact @mess_support for assistance
        """

        await query.edit_message_text(help_text, parse_mode='Markdown')

    async def admin_callback(self, update: Update, context):
        """Handle admin button callback"""
        query = update.callback_query
        user = update.effective_user

        if user.id not in self.admin_ids:
            await query.edit_message_text("Unauthorized")
            return

        keyboard = [
            [InlineKeyboardButton("👥 Pending Registrations", callback_data='admin_registrations')],
            [InlineKeyboardButton("💰 Pending Payments", callback_data='admin_payments')],
            [InlineKeyboardButton("📊 Statistics", callback_data='admin_stats')],
            [InlineKeyboardButton("🔧 System Settings", callback_data='admin_settings')],
            [InlineKeyboardButton("🔙 Back to Main", callback_data='back_to_main')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔧 **Admin Panel**\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def back_to_main_callback(self, update: Update, context):
        """Handle back to main button callback"""
        query = update.callback_query
        user = update.effective_user

        keyboard = [
            [InlineKeyboardButton("📝 Register", callback_data='register')],
            [InlineKeyboardButton("💳 Upload Payment", callback_data='payment')],
            [InlineKeyboardButton("✂️ Take Mess Cut", callback_data='messcut')],
            [InlineKeyboardButton("🎫 My QR", callback_data='myqr')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]

        if user.id in self.admin_ids:
            keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data='admin')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = f"""
Welcome to Mess Management System, {user.first_name}! 👋

I'm here to help you manage your mess operations. Use the buttons below to:

• Register for mess access
• Upload payment screenshots
• Apply for mess cuts
• View your QR code
• Get help and support

Please select an option to continue:
        """

        await query.edit_message_text(welcome_text, reply_markup=reply_markup)

    async def register_command(self, update: Update, context):
        """Handle registration flow"""
        user = update.effective_user

        # Check if already registered
        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            await update.message.reply_text(
                f"You're already registered with status: {student.status}"
            )
            return
        except Student.DoesNotExist:
            pass

        # Start registration flow
        context.user_data['registration_flow'] = {'step': 'name'}
        await update.message.reply_text(
            "Let's start your registration!\n\nPlease enter your full name:"
        )
    
    async def payment_command(self, update: Update, context):
        """Handle payment upload flow"""
        user = update.effective_user
        
        # Check if registered and approved
        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            if student.status != StudentStatus.APPROVED:
                await update.message.reply_text(
                    "Your registration is not approved yet. Please wait for admin approval."
                )
                return
        except Student.DoesNotExist:
            await update.message.reply_text(
                "Please register first using /register"
            )
            return
        
        # Start payment flow
        context.user_data['payment_flow'] = {
            'step': 'cycle_start',
            'student_id': student.id
        }
        
        keyboard = [
            [InlineKeyboardButton("Current Month", callback_data='payment_current')],
            [InlineKeyboardButton("Next Month", callback_data='payment_next')],
            [InlineKeyboardButton("Custom Dates", callback_data='payment_custom')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Select payment cycle:",
            reply_markup=reply_markup
        )
    
    async def messcut_command(self, update: Update, context):
        """Handle mess cut application"""
        user = update.effective_user
        
        # Check if registered and approved
        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            if student.status != StudentStatus.APPROVED:
                await update.message.reply_text(
                    "Your registration is not approved yet."
                )
                return
        except Student.DoesNotExist:
            await update.message.reply_text(
                "Please register first using /register"
            )
            return
        
        # Check cutoff time
        if not is_within_cutoff_time():
            await update.message.reply_text(
                "⏰ Cutoff time (11:00 PM) has passed. You can only apply for dates starting day after tomorrow."
            )
        
        # Start mess cut flow
        context.user_data['messcut_flow'] = {
            'step': 'from_date',
            'student_id': student.id
        }
        
        await update.message.reply_text(
            "Enter the start date for mess cut (DD-MM-YYYY):"
        )
    
    async def myqr_command(self, update: Update, context):
        """Show student's QR code"""
        user = update.effective_user
        
        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            if student.status != StudentStatus.APPROVED:
                await update.message.reply_text(
                    "Your registration is not approved yet."
                )
                return
            
            # Generate QR code
            qr_payload = student.generate_qr_payload(settings.QR_SECRET)
            qr_image = generate_qr_code(qr_payload)
            
            await update.message.reply_photo(
                photo=qr_image,
                caption="🎫 Your permanent QR code. Please don't share this with anyone."
            )
            
        except Student.DoesNotExist:
            await update.message.reply_text(
                "Please register first using /register"
            )
    
    async def status_command(self, update: Update, context):
        """Show student status"""
        user = update.effective_user
        
        try:
            student = await sync_to_async(Student.objects.get)(tg_user_id=user.id)
            
            # Get payment status
            current_payment = await sync_to_async(student.payments.filter(
                status=PaymentStatus.VERIFIED,
                cycle_start__lte=datetime.now().date(),
                cycle_end__gte=datetime.now().date()
            ).first)()

            # Get active mess cuts
            active_cuts = await sync_to_async(student.mess_cuts.filter(
                from_date__lte=datetime.now().date(),
                to_date__gte=datetime.now().date()
            ).count)()
            
            status_text = f"""
📊 **Your Status**

Name: {student.name}
Roll No: {student.roll_no}
Room: {student.room_no}
Registration: {student.status}
Payment: {'✅ Valid' if current_payment else '❌ Not Valid'}
Active Cuts: {active_cuts}
QR Version: {student.qr_version}
            """
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Student.DoesNotExist:
            await update.message.reply_text(
                "You are not registered. Use /register to start."
            )
    
    async def admin_command(self, update: Update, context):
        """Admin panel"""
        user = update.effective_user
        
        if user.id not in self.admin_ids:
            await update.message.reply_text("Unauthorized")
            return
        
        keyboard = [
            [InlineKeyboardButton("Pending Registrations", callback_data='admin_registrations')],
            [InlineKeyboardButton("Pending Payments", callback_data='admin_payments')],
            [InlineKeyboardButton("Mess Closures", callback_data='admin_closures')],
            [InlineKeyboardButton("Regenerate All QR", callback_data='admin_qr_regen')],
            [InlineKeyboardButton("Reports", callback_data='admin_reports')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 **Admin Panel**\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_callback(self, update: Update, context):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data

        # Route to appropriate handler
        if data == 'register':
            await self.register_callback(update, context)
        elif data == 'payment':
            await self.payment_callback(update, context)
        elif data == 'messcut':
            await self.messcut_callback(update, context)
        elif data == 'myqr':
            await self.myqr_callback(update, context)
        elif data == 'help':
            await self.help_callback(update, context)
        elif data == 'admin':
            await self.admin_callback(update, context)
        elif data == 'back_to_main':
            await self.back_to_main_callback(update, context)
        elif data.startswith('admin_'):
            await self.handle_admin_callback(update, context, data)
        elif data.startswith('payment_'):
            await self.handle_payment_callback(update, context, data)
    
    async def handle_admin_callback(self, update: Update, context, data: str):
        """Handle admin panel callbacks"""
        query = update.callback_query
        user = update.effective_user
        
        if user.id not in self.admin_ids:
            await query.edit_message_text("Unauthorized")
            return

        if data == 'admin_registrations':
            # Show pending registrations
            pending = await sync_to_async(list)(Student.objects.filter(status=StudentStatus.PENDING))

            if not pending:
                await query.edit_message_text("No pending registrations")
                return
            
            # Show first pending registration
            student = pending[0]
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f'approve_{student.id}'),
                    InlineKeyboardButton("❌ Deny", callback_data=f'deny_{student.id}')
                ],
                [InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            text = f"""
👥 **Pending Registration** ({len(pending)} total)

**Name:** {student.name}
**Roll:** {student.roll_no}
**Room:** {student.room_no}
**Phone:** {student.phone}
**Registered:** {student.created_at.strftime('%Y-%m-%d %H:%M')}

Choose an action:
            """

            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif data.startswith('approve_') or data.startswith('deny_'):
            # Process approval/denial
            action, student_id = data.split('_')
            student = await sync_to_async(Student.objects.get)(id=int(student_id))
            
            if action == 'approve':
                student.status = StudentStatus.APPROVED
                message = "✅ Registration approved!"
                
                # Generate and send QR
                qr_payload = student.generate_qr_payload(settings.QR_SECRET)
                qr_image = generate_qr_code(qr_payload)
                
                send_telegram_notification.delay(
                    student.tg_user_id,
                    message,
                    attachment=qr_image
                )
            else:
                student.status = StudentStatus.DENIED
                message = "❌ Registration denied."
                send_telegram_notification.delay(student.tg_user_id, message)
            
            await sync_to_async(student.save)()
            await query.edit_message_text(f"Student {action}d successfully")

        elif data == 'admin_payments':
            await query.edit_message_text(
                "💰 **Payment Management**\n\nPayment verification features coming soon!",
                parse_mode='Markdown'
            )

        elif data == 'admin_stats':
            # Get basic stats
            total_students = await sync_to_async(Student.objects.count)()
            pending_students = await sync_to_async(Student.objects.filter(status=StudentStatus.PENDING).count)()
            approved_students = await sync_to_async(Student.objects.filter(status=StudentStatus.APPROVED).count)()

            stats_text = f"""
📊 **System Statistics**

👥 **Students:**
• Total: {total_students}
• Pending: {pending_students}
• Approved: {approved_students}

🔙 Use the back button to return to admin panel.
            """

            keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data='admin')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        elif data == 'admin_settings':
            await query.edit_message_text(
                "🔧 **System Settings**\n\nSettings management features coming soon!",
                parse_mode='Markdown'
            )
    
    async def handle_photo(self, update: Update, context):
        """Handle photo uploads (for payments)"""
        if 'payment_flow' not in context.user_data:
            await update.message.reply_text(
                "Please use /payment to start payment upload process"
            )
            return
        
        flow = context.user_data['payment_flow']
        
        if flow.get('step') == 'screenshot':
            # Save payment screenshot
            photo = update.message.photo[-1]  # Get highest resolution
            file = await photo.get_file()
            
            # Upload to Cloudinary
            from core.utils import upload_to_cloudinary
            screenshot_url = upload_to_cloudinary(file)
            
            # Create payment record
            payment = await sync_to_async(Payment.objects.create)(
                student_id=flow['student_id'],
                cycle_start=flow['cycle_start'],
                cycle_end=flow['cycle_end'],
                amount=flow['amount'],
                screenshot_url=screenshot_url,
                status=PaymentStatus.UPLOADED
            )
            
            # Clear flow
            del context.user_data['payment_flow']
            
            await update.message.reply_text(
                "✅ Payment uploaded successfully! Awaiting admin verification."
            )
            
            # Notify admins
            for admin_id in self.admin_ids:
                send_telegram_notification.delay(
                    admin_id,
                    f"New payment uploaded by {payment.student.roll_no}"
                )
    
    async def handle_text(self, update: Update, context):
        """Handle text messages based on current flow"""
        text = update.message.text
        user = update.effective_user
        
        # Registration flow
        if 'registration_flow' in context.user_data:
            await self.handle_registration_flow(update, context, text)
        
        # Payment flow
        elif 'payment_flow' in context.user_data:
            await self.handle_payment_flow(update, context, text)
        
        # Mess cut flow
        elif 'messcut_flow' in context.user_data:
            await self.handle_messcut_flow(update, context, text)
        
        else:
            await update.message.reply_text(
                "Please use a command to start. Type /help for available commands."
            )
    
    async def handle_registration_flow(self, update: Update, context, text: str):
        """Handle registration data collection"""
        flow = context.user_data['registration_flow']
        step = flow.get('step')
        
        if step == 'name':
            flow['name'] = text
            flow['step'] = 'roll_no'
            await update.message.reply_text("Enter your roll number:")
        
        elif step == 'roll_no':
            flow['roll_no'] = text.upper()
            flow['step'] = 'room_no'
            await update.message.reply_text("Enter your room number:")
        
        elif step == 'room_no':
            flow['room_no'] = text
            flow['step'] = 'phone'
            await update.message.reply_text("Enter your phone number:")
        
        elif step == 'phone':
            flow['phone'] = text
            
            # Create student record
            student = await sync_to_async(Student.objects.create)(
                tg_user_id=update.effective_user.id,
                name=flow['name'],
                roll_no=flow['roll_no'],
                room_no=flow['room_no'],
                phone=flow['phone'],
                status=StudentStatus.PENDING
            )
            
            # Clear flow
            del context.user_data['registration_flow']
            
            await update.message.reply_text(
                "✅ Registration submitted! Awaiting admin approval."
            )
            
            # Notify admins
            for admin_id in self.admin_ids:
                send_telegram_notification.delay(
                    admin_id,
                    f"New registration: {student.name} ({student.roll_no})"
                )


# Global bot instance
_bot_instance = None

def get_bot_instance():
    """Get or create a global bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TelegramBot()
        # Initialize the application synchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def init_bot():
            await _bot_instance.application.initialize()

        loop.run_until_complete(init_bot())
        logger.info("Bot instance initialized successfully")

    return _bot_instance


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    """Webhook endpoint for Telegram updates"""

    def post(self, request):
        """Process webhook update"""
        try:
            data = json.loads(request.body)
            logger.info(f"Received webhook update: {data}")

            # Get the initialized bot instance
            bot = get_bot_instance()

            # Create update object
            update = Update.de_json(data, bot.application.bot)

            # Process the update synchronously
            import asyncio

            async def process_update():
                try:
                    await bot.application.process_update(update)
                    logger.info("Update processed successfully")
                except Exception as e:
                    logger.error(f"Error processing update: {e}")

            # Run the async function
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(process_update())

            return JsonResponse({'ok': True})
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)