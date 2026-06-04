          // Web Search Toggle
          BlocBuilder<ChatBloc, ChatState>(
            builder: (context, state) {
              return Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                child: GestureDetector(
                  onTap: () => context.read<ChatBloc>().add(const ChatWebSearchToggled()),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      color: state.webSearchEnabled
                          ? const Color(0xFF2563eb).withOpacity(0.15)
                          : const Color(0xFF1f2937),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: state.webSearchEnabled
                            ? const Color(0xFF2563eb)
                            : const Color(0xFF374151),
                        width: 1,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.language,
                          size: 16,
                          color: state.webSearchEnabled
                              ? const Color(0xFF60a5fa)
                              : const Color(0xFF9ca3af),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          '联网搜索',
                          style: TextStyle(
                            fontSize: 13,
                            color: state.webSearchEnabled
                                ? const Color(0xFF60a5fa)
                                : const Color(0xFF9ca3af),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Icon(
                          state.webSearchEnabled ? Icons.toggle_on : Icons.toggle_off,
                          size: 20,
                          color: state.webSearchEnabled
                              ? const Color(0xFF2563eb)
                              : const Color(0xFF6b7280),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),

