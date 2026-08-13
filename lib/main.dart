import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'app_theme.dart';
import 'task_provider.dart';
import 'theme_provider.dart';

void main() {
  runApp(
    const ProviderScope(
      child: NudgeApp(),
    ),
  );
}

class NudgeApp extends ConsumerWidget {
  const NudgeApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeProvider);

    return MaterialApp(
      title: 'Nudge',
      debugShowCheckedModeBanner: false,
      locale: const Locale('ar'),
      supportedLocales: const [
        Locale('ar'),
        Locale('en'),
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeMode,
      home: const MainNavigationScreen(),
    );
  }
}

class MainNavigationScreen extends ConsumerStatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  ConsumerState<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends ConsumerState<MainNavigationScreen> {
  int _currentIndex = 0;
  TaskCategory? _selectedCategoryFilter;
  String _searchQuery = '';
  bool _isSearching = false;

  @override
  Widget build(BuildContext context) {
    final allTasks = ref.watch(tasksProvider);
    final currentThemeMode = ref.watch(themeProvider);

    final activeTasks = allTasks.where((t) => !t.isCompleted).toList();
    final completedTasks = allTasks.where((t) => t.isCompleted).toList();

    final filteredActiveTasks = activeTasks.where((t) {
      final matchesCategory = _selectedCategoryFilter == null || t.category == _selectedCategoryFilter;
      final matchesSearch = t.title.toLowerCase().contains(_searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    }).toList();

    return Scaffold(
appBar: AppBar(
      title: _isSearching
          ? TextField(
              autofocus: true,
              decoration: const InputDecoration(
                hintText: '...ابحث عن مهمة',
                border: InputBorder.none,
              ),
              onChanged: (value) {
                setState(() => _searchQuery = value);
              },
            )
          : Text(_currentIndex == 0 ? 'اليوم' : 'الإنجازات المكتملة'),
      elevation: 0,
      actions: [
        // 1. زر مسح المكتملات (يظهر فقط في تبويب المكتملات)
        if (_currentIndex == 1)
          IconButton(
            icon: const Icon(Icons.delete_sweep_outlined),
            tooltip: 'مسح جميع المكتملات',
            onPressed: () {
              final completedTasks = ref.read(tasksProvider).where((t) => t.isCompleted).toList();
              if (completedTasks.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('لا توجد مهام مكتملة لمسحها')),
                );
                return;
              }

              showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('مسح المهام المكتملة'),
                  content: const Text('هل أنت تأكد من مسح جميع المهام المكتملة؟ لا يمكن التراجع عن هذا الإجراء.'),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text('إلغاء'),
                    ),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        foregroundColor: Colors.white,
                      ),
                      onPressed: () {
                        ref.read(tasksProvider.notifier).clearCompletedTasks();
                        Navigator.pop(ctx);
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('تم مسح جميع المهام المكتملة بنجاح')),
                        );
                      },
                      child: const Text('مسح الكل'),
                    ),
                  ],
                ),
              );
            },
          ),

        // 2. زر تغيير الثيم
        IconButton(
          icon: Icon(
            currentThemeMode == ThemeMode.dark
                ? Icons.light_mode
                : Icons.dark_mode_outlined,
          ),
          onPressed: () {
            ref.read(themeProvider.notifier).toggleTheme();
          },
        ),

        // 3. زر البحث (يظهر فقط في تبويب اليوم)
        if (_currentIndex == 0)
          IconButton(
            icon: Icon(_isSearching ? Icons.close : Icons.search),
            onPressed: () {
              setState(() {
                _isSearching = !_isSearching;
                if (!_isSearching) _searchQuery = '';
              });
            },
          ),
      ],
    ),
      body: _currentIndex == 0
          ? Column(
              children: [
                _buildProgressBar(allTasks.length, completedTasks.length),
                _buildCategoryFilterChips(),
                Expanded(child: _buildActiveTasksList(filteredActiveTasks)),
              ],
            )
          : _buildCompletedTasksList(completedTasks),
      
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
            _isSearching = false;
            _searchQuery = '';
          });
        },
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.today_outlined),
            selectedIcon: const Icon(Icons.today),
            label: 'اليوم (${activeTasks.length})',
          ),
          NavigationDestination(
            icon: const Icon(Icons.check_circle_outline),
            selectedIcon: const Icon(Icons.check_circle),
            label: 'المكتملة (${completedTasks.length})',
          ),
        ],
      ),

      floatingActionButton: _currentIndex == 0
          ? FloatingActionButton.extended(
              onPressed: () => _showTaskFormSheet(context),
              icon: const Icon(Icons.add),
              label: const Text('مهمة جديدة'),
            )
          : null,
    );
  }

  Widget _buildProgressBar(int totalCount, int completedCount) {
    if (totalCount == 0) return const SizedBox();

    final double progress = completedCount / totalCount;
    final int percentage = (progress * 100).toInt();

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.primary.withAlpha(20),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'تقدمك اليوم: $percentage%',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              Text(
                '$completedCount من $totalCount مهام',
                style: const TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 8,
              backgroundColor: Colors.grey.shade300,
              valueColor: const AlwaysStoppedAnimation<Color>(AppColors.primary),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCategoryFilterChips() {
    final categories = [
      {'title': 'الكل', 'icon': '', 'category': null},
      {'title': 'شخصي', 'icon': '👤', 'category': TaskCategory.personal},
      {'title': 'العمل', 'icon': '💼', 'category': TaskCategory.work},
      {'title': 'الدراسة', 'icon': '📚', 'category': TaskCategory.study},
      {'title': 'التسوق', 'icon': '🛒', 'category': TaskCategory.shopping},
    ];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: categories.map((item) {
          final cat = item['category'] as TaskCategory?;
          final isSelected = _selectedCategoryFilter == cat;
          final icon = item['icon'] as String;
          final title = item['title'] as String;

          return Padding(
            padding: const EdgeInsets.only(left: 8),
            child: InkWell(
              onTap: () => setState(() => _selectedCategoryFilter = cat),
              borderRadius: BorderRadius.circular(10),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.primary : Colors.transparent,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: isSelected ? AppColors.primary : Colors.grey.shade400,
                    width: 1.5,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (icon.isNotEmpty) ...[
                      Text(icon, style: const TextStyle(fontSize: 14)),
                      const SizedBox(width: 6),
                    ],
                    Text(
                      title,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                        color: isSelected ? Colors.white : Theme.of(context).textTheme.bodyLarge?.color,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildActiveTasksList(List<Task> tasks) {
    if (tasks.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.wb_sunny_outlined, size: 72, color: AppColors.primary),
            const SizedBox(height: 16),
            Text(
              _searchQuery.isNotEmpty ? 'لا توجد نتائج' : 'لا توجد مهام حالياً ✨',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: tasks.length,
      itemBuilder: (context, index) {
        final task = tasks[index];
        final completedSubCount = task.subtasks.where((s) => s.isCompleted).length;

        return Dismissible(
          key: Key(task.id),
          background: Container(
            alignment: Alignment.centerRight,
            padding: const EdgeInsets.only(right: 20),
            margin: const EdgeInsets.only(bottom: 10),
            decoration: BoxDecoration(
              color: Colors.green.shade600,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.start,
              children: [
                SizedBox(width: 20),
                Icon(Icons.check_circle_outline, color: Colors.white, size: 28),
                SizedBox(width: 8),
                Text('إنجاز', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          secondaryBackground: Container(
            alignment: Alignment.centerLeft,
            padding: const EdgeInsets.only(left: 20),
            margin: const EdgeInsets.only(bottom: 10),
            decoration: BoxDecoration(
              color: Colors.redAccent,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text('حذف', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                SizedBox(width: 8),
                Icon(Icons.delete_outline, color: Colors.white, size: 28),
                SizedBox(width: 20),
              ],
            ),
          ),
          onDismissed: (direction) {
            if (direction == DismissDirection.startToEnd) {
              ref.read(tasksProvider.notifier).toggleTask(task.id);
            } else {
              ref.read(tasksProvider.notifier).deleteTask(task.id);
            }
          },
          child: Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: ListTile(
              onTap: () => _showTaskDetailSheet(context, task),
              leading: Checkbox(
                value: task.isCompleted,
                activeColor: AppColors.primary,
                shape: const CircleBorder(),
                onChanged: (_) {
                  ref.read(tasksProvider.notifier).toggleTask(task.id);
                },
              ),
              title: Text(task.title),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Wrap(
                  spacing: 12,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(task.category.title, style: const TextStyle(fontSize: 12)),
                    if (task.dueDate != null) ...[
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.access_time_rounded, size: 13, color: Colors.grey),
                          const SizedBox(width: 4),
                          Text(
                            _formatDateTime(task.dueDate!),
                            style: const TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                        ],
                      ),
                    ],
                    if (task.subtasks.isNotEmpty)
                      Text('📋 $completedSubCount/${task.subtasks.length}', style: const TextStyle(fontSize: 12, color: AppColors.primary)),
                  ],
                ),
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(shape: BoxShape.circle, color: _getPriorityColor(task.priority)),
                  ),
                  IconButton(
                    icon: const Icon(Icons.edit_outlined, color: Colors.blueAccent),
                    onPressed: () => _showTaskFormSheet(context, taskToEdit: task),
                  ),
                  IconButton(
                    icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                    onPressed: () => ref.read(tasksProvider.notifier).deleteTask(task.id),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  String _formatDateTime(DateTime dt) {
    final dateStr = DateFormat('yyyy/MM/dd').format(dt);
    final hour = dt.hour == 0 ? 12 : (dt.hour > 12 ? dt.hour - 12 : dt.hour);
    final period = dt.hour >= 12 ? 'م' : 'ص';
    final minute = dt.minute.toString().padLeft(2, '0');
    return '$dateStr | $hour:$minute $period';
  }

  Widget _buildCompletedTasksList(List<Task> tasks) {
    if (tasks.isEmpty) {
      return const Center(child: Text('لم تكمل أي مهمة بعد.. 🚀', style: TextStyle(color: Colors.grey)));
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: tasks.length,
      itemBuilder: (context, index) {
        final task = tasks[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          child: ListTile(
            leading: Checkbox(
              value: task.isCompleted,
              activeColor: Colors.grey,
              shape: const CircleBorder(),
              onChanged: (_) => ref.read(tasksProvider.notifier).toggleTask(task.id),
            ),
            title: Text(task.title, style: const TextStyle(decoration: TextDecoration.lineThrough, color: Colors.grey)),
            trailing: IconButton(
              icon: const Icon(Icons.delete_outline, color: Colors.grey),
              onPressed: () => ref.read(tasksProvider.notifier).deleteTask(task.id),
            ),
          ),
        );
      },
    );
  }

  Color _getPriorityColor(TaskPriority priority) {
    switch (priority) {
      case TaskPriority.urgent:
        return Colors.red;
      case TaskPriority.high:
        return Colors.orange;
      case TaskPriority.low:
        return Colors.grey;
      default:
        return AppColors.primary;
    }
  }

  void _showTaskFormSheet(BuildContext context, {Task? taskToEdit}) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => TaskFormBottomSheet(taskToEdit: taskToEdit),
    );
  }

  void _showTaskDetailSheet(BuildContext context, Task task) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => TaskDetailBottomSheet(taskId: task.id),
    );
  }
}

class TaskDetailBottomSheet extends ConsumerStatefulWidget {
  final String taskId;
  const TaskDetailBottomSheet({super.key, required this.taskId});

  @override
  ConsumerState<TaskDetailBottomSheet> createState() => _TaskDetailBottomSheetState();
}

class _TaskDetailBottomSheetState extends ConsumerState<TaskDetailBottomSheet> {
  final _subTaskController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final tasks = ref.watch(tasksProvider);
    final taskList = tasks.where((t) => t.id == widget.taskId).toList();

    if (taskList.isEmpty) return const SizedBox();
    final task = taskList.first;

    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(task.title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const Divider(height: 24),
          const Text('المهام الفرعية:', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          ...task.subtasks.map((sub) => CheckboxListTile(
                value: sub.isCompleted,
                title: Text(sub.title, style: TextStyle(decoration: sub.isCompleted ? TextDecoration.lineThrough : null)),
                onChanged: (_) {
                  ref.read(tasksProvider.notifier).toggleSubTask(task.id, sub.id);
                },
              )),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _subTaskController,
                  decoration: const InputDecoration(
                    hintText: 'إضافة خطوة فرعية...',
                    border: InputBorder.none,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.add_circle, color: AppColors.primary),
                onPressed: () {
                  if (_subTaskController.text.trim().isNotEmpty) {
                    ref.read(tasksProvider.notifier).addSubTask(task.id, _subTaskController.text);
                    _subTaskController.clear();
                  }
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// نافذة إضافة / تعديل المهمة
class TaskFormBottomSheet extends ConsumerStatefulWidget {
  final Task? taskToEdit;
  const TaskFormBottomSheet({super.key, this.taskToEdit});

  @override
  ConsumerState<TaskFormBottomSheet> createState() => _TaskFormBottomSheetState();
}

class _TaskFormBottomSheetState extends ConsumerState<TaskFormBottomSheet> {
  late TextEditingController _controller;
  DateTime? _selectedDate;
  TimeOfDay? _selectedTime;
  TaskPriority _selectedPriority = TaskPriority.normal;
  TaskCategory _selectedCategory = TaskCategory.personal;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.taskToEdit?.title ?? '');
    if (widget.taskToEdit != null) {
      _selectedDate = widget.taskToEdit!.dueDate;
      if (widget.taskToEdit!.dueDate != null) {
        _selectedTime = TimeOfDay.fromDateTime(widget.taskToEdit!.dueDate!);
      }
      _selectedPriority = widget.taskToEdit!.priority;
      _selectedCategory = widget.taskToEdit!.category;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isEditing = widget.taskToEdit != null;

    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _controller,
            autofocus: true,
            decoration: InputDecoration(
              hintText: isEditing ? 'تعديل المهمة...' : 'ما الذي تريد إنجازه اليوم؟',
              border: InputBorder.none,
            ),
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                DropdownButton<TaskCategory>(
                  value: _selectedCategory,
                  underline: const SizedBox(),
                  items: TaskCategory.values.map((cat) {
                    return DropdownMenuItem(value: cat, child: Text(cat.title));
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) setState(() => _selectedCategory = val);
                  },
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: _pickDate,
                  icon: const Icon(Icons.calendar_month, size: 16),
                  label: Text(
                    _selectedDate == null ? 'التاريخ' : DateFormat('MM/dd').format(_selectedDate!),
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton.icon(
                  onPressed: _pickTime,
                  icon: const Icon(Icons.access_time, size: 16),
                  label: Text(
                    _selectedTime == null
                        ? 'الوقت'
                        : '${_selectedTime!.hourOfPeriod == 0 ? 12 : _selectedTime!.hourOfPeriod}:${_selectedTime!.minute.toString().padLeft(2, '0')} ${_selectedTime!.period == DayPeriod.am ? 'ص' : 'م'}',
                  ),
                ),
                const SizedBox(width: 8),
                DropdownButton<TaskPriority>(
                  value: _selectedPriority,
                  underline: const SizedBox(),
                  items: const [
                    DropdownMenuItem(value: TaskPriority.normal, child: Text('عادية')),
                    DropdownMenuItem(value: TaskPriority.high, child: Text('عالية')),
                    DropdownMenuItem(value: TaskPriority.urgent, child: Text('عاجلة 🔥')),
                  ],
                  onChanged: (val) {
                    if (val != null) setState(() => _selectedPriority = val);
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerLeft,
            child: ElevatedButton(
              onPressed: _submit,
              child: Text(isEditing ? 'حفظ التعديلات' : 'إضافة'),
            ),
          ),
        ],
      ),
    );
  }

  void _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate ?? DateTime.now(),
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) setState(() => _selectedDate = picked);
  }

  void _pickTime() async {
    final time = await showTimePicker(
      context: context,
      initialTime: _selectedTime ?? TimeOfDay.now(),
    );
    if (time != null) setState(() => _selectedTime = time);
  }

  void _submit() {
    if (_controller.text.trim().isNotEmpty) {
      DateTime? finalDateTime = _selectedDate;
      if (_selectedDate != null && _selectedTime != null) {
        finalDateTime = DateTime(
          _selectedDate!.year,
          _selectedDate!.month,
          _selectedDate!.day,
          _selectedTime!.hour,
          _selectedTime!.minute,
        );
      }

      if (widget.taskToEdit != null) {
        ref.read(tasksProvider.notifier).updateTask(
              widget.taskToEdit!.id,
              title: _controller.text,
              dueDate: finalDateTime,
              priority: _selectedPriority,
              category: _selectedCategory,
            );
      } else {
        ref.read(tasksProvider.notifier).addTask(
              _controller.text,
              dueDate: finalDateTime,
              priority: _selectedPriority,
              category: _selectedCategory,
            );
      }
      Navigator.pop(context);
    }
  }
}