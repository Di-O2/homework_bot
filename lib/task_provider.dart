import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum TaskPriority { low, normal, high, urgent }
enum TaskCategory { personal, work, study, shopping }

extension TaskCategoryExtension on TaskCategory {
  String get title {
    switch (this) {
      case TaskCategory.work:
        return '💼 العمل';
      case TaskCategory.study:
        return '📚 الدراسة';
      case TaskCategory.shopping:
        return '🛒 التسوق';
      case TaskCategory.personal:
        return '👤 شخصي';
    }
  }
}

class SubTask {
  final String id;
  final String title;
  final bool isCompleted;

  SubTask({
    required this.id,
    required this.title,
    this.isCompleted = false,
  });

  SubTask copyWith({String? id, String? title, bool? isCompleted}) {
    return SubTask(
      id: id ?? this.id,
      title: title ?? this.title,
      isCompleted: isCompleted ?? this.isCompleted,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'isCompleted': isCompleted,
      };

  factory SubTask.fromJson(Map<String, dynamic> json) => SubTask(
        id: json['id'],
        title: json['title'],
        isCompleted: json['isCompleted'] ?? false,
      );
}

class Task {
  final String id;
  final String title;
  final bool isCompleted;
  final DateTime? dueDate;
  final TaskPriority priority;
  final TaskCategory category;
  final List<SubTask> subtasks;

  Task({
    required this.id,
    required this.title,
    this.isCompleted = false,
    this.dueDate,
    this.priority = TaskPriority.normal,
    this.category = TaskCategory.personal,
    this.subtasks = const [],
  });

  Task copyWith({
    String? id,
    String? title,
    bool? isCompleted,
    DateTime? dueDate,
    TaskPriority? priority,
    TaskCategory? category,
    List<SubTask>? subtasks,
  }) {
    return Task(
      id: id ?? this.id,
      title: title ?? this.title,
      isCompleted: isCompleted ?? this.isCompleted,
      dueDate: dueDate,
      priority: priority ?? this.priority,
      category: category ?? this.category,
      subtasks: subtasks ?? this.subtasks,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'isCompleted': isCompleted,
        'dueDate': dueDate?.toIso8601String(),
        'priority': priority.index,
        'category': category.index,
        'subtasks': subtasks.map((s) => s.toJson()).toList(),
      };

  factory Task.fromJson(Map<String, dynamic> json) => Task(
        id: json['id'],
        title: json['title'],
        isCompleted: json['isCompleted'] ?? false,
        dueDate: json['dueDate'] != null ? DateTime.parse(json['dueDate']) : null,
        priority: TaskPriority.values[json['priority'] ?? 1],
        category: TaskCategory.values[json['category'] ?? 0],
        subtasks: (json['subtasks'] as List<dynamic>?)
                ?.map((s) => SubTask.fromJson(s))
                .toList() ??
            [],
      );
}

class TasksNotifier extends StateNotifier<List<Task>> {
  static const _storageKey = 'nudge_tasks_data';

  TasksNotifier() : super([]) {
    _loadTasks();
  }

  Future<void> _loadTasks() async {
    final prefs = await SharedPreferences.getInstance();
    final String? tasksJson = prefs.getString(_storageKey);
    if (tasksJson != null) {
      final List<dynamic> decoded = jsonDecode(tasksJson);
      state = decoded.map((item) => Task.fromJson(item)).toList();
    }
  }

  Future<void> _saveTasks() async {
    final prefs = await SharedPreferences.getInstance();
    final String encoded = jsonEncode(state.map((t) => t.toJson()).toList());
    await prefs.setString(_storageKey, encoded);
  }

  void addTask(
    String title, {
    DateTime? dueDate,
    TaskPriority priority = TaskPriority.normal,
    TaskCategory category = TaskCategory.personal,
  }) {
    if (title.trim().isEmpty) return;
    final newTask = Task(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: title.trim(),
      dueDate: dueDate,
      priority: priority,
      category: category,
    );
    state = [...state, newTask];
    _saveTasks();
  }

  void updateTask(
    String id, {
    required String title,
    DateTime? dueDate,
    TaskPriority priority = TaskPriority.normal,
    TaskCategory category = TaskCategory.personal,
  }) {
    if (title.trim().isEmpty) return;
    state = [
      for (final task in state)
        if (task.id == id)
          task.copyWith(
            title: title.trim(),
            dueDate: dueDate,
            priority: priority,
            category: category,
          )
        else
          task,
    ];
    _saveTasks();
  }

  void toggleTask(String id) {
    state = [
      for (final task in state)
        if (task.id == id)
          task.copyWith(isCompleted: !task.isCompleted)
        else
          task,
    ];
    _saveTasks();
  }

void deleteTask(String id) {
    state = state.where((task) => task.id != id).toList();
    _saveTasks();
  }

  // 👈 الصق الدالة الجديدة هنا بالضبط
  void clearCompletedTasks() {
    state = state.where((task) => !task.isCompleted).toList();
    _saveTasks();
  }

  void addSubTask(String taskId, String subTaskTitle) {
    if (subTaskTitle.trim().isEmpty) return;
    state = [
      for (final task in state)
        if (task.id == taskId)
          task.copyWith(
            subtasks: [
              ...task.subtasks,
              SubTask(
                id: DateTime.now().millisecondsSinceEpoch.toString(),
                title: subTaskTitle.trim(),
              ),
            ],
          )
        else
          task,
    ];
    _saveTasks();
  }

  void toggleSubTask(String taskId, String subTaskId) {
    state = [
      for (final task in state)
        if (task.id == taskId)
          task.copyWith(
            subtasks: [
              for (final sub in task.subtasks)
                if (sub.id == subTaskId)
                  sub.copyWith(isCompleted: !sub.isCompleted)
                else
                  sub,
            ],
          )
        else
          task,
    ];
    _saveTasks();
  }
}

final tasksProvider = StateNotifierProvider<TasksNotifier, List<Task>>((ref) {
  return TasksNotifier();
});