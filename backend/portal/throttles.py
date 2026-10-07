from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class LoginThrottle(AnonRateThrottle):
    rate = '10/min'

class RegisterThrottle(AnonRateThrottle):
    rate = '5/hour'

class BookingCreateThrottle(UserRateThrottle):
    rate = '20/hour'
