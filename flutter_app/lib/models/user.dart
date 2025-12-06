/// User model
class User {
  final String id;
  final String email;
  final String? fullName;
  final bool isActive;
  final int storageQuotaMb;
  final DateTime createdAt;

  User({
    required this.id,
    required this.email,
    this.fullName,
    required this.isActive,
    required this.storageQuotaMb,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      email: json['email'] as String,
      fullName: json['full_name'] as String?,
      isActive: json['is_active'] as bool,
      storageQuotaMb: json['storage_quota_mb'] as int,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'is_active': isActive,
      'storage_quota_mb': storageQuotaMb,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
