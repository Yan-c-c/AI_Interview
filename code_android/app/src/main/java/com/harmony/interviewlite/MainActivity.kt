package com.harmony.interviewlite

import android.graphics.Color as AndroidColor
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyGridScope
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items as gridItems
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.harmony.interviewlite.data.AgentShortcut
import com.harmony.interviewlite.data.AgentShortcuts
import com.harmony.interviewlite.data.ChatMessage
import com.harmony.interviewlite.data.ChatRole
import com.harmony.interviewlite.data.HistoryRecord
import com.harmony.interviewlite.data.intentLabel
import com.harmony.interviewlite.ui.theme.HarmonyLiteTheme

private val AppBackground = Color(0xFFF7F8FA)
private val LineColor = Color(0xFFE1E7EF)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            HarmonyLiteTheme {
                val viewModel: HarmonyViewModel = viewModel()
                HarmonyApp(viewModel)
            }
        }
    }
}

@Composable
private fun HarmonyApp(viewModel: HarmonyViewModel) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = AppBackground
    ) {
        when {
            !viewModel.isReady -> LoadingScreen()
            !viewModel.isAuthenticated -> AuthScreen(viewModel)
            else -> MainShell(viewModel)
        }
    }
}

@Composable
private fun LoadingScreen() {
    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        CircularProgressIndicator()
        Spacer(Modifier.height(14.dp))
        Text("正在校验登录状态", color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun AuthScreen(viewModel: HarmonyViewModel) {
    var loginEmail by rememberSaveable { mutableStateOf("") }
    var loginPassword by rememberSaveable { mutableStateOf("") }
    var registerName by rememberSaveable { mutableStateOf("") }
    var registerEmail by rememberSaveable { mutableStateOf("") }
    var registerPassword by rememberSaveable { mutableStateOf("") }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 22.dp, vertical = 44.dp),
        verticalArrangement = Arrangement.spacedBy(22.dp)
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(MaterialTheme.colorScheme.primary),
                    contentAlignment = Alignment.Center
                ) {
                    Text("AI", color = Color.White, fontWeight = FontWeight.Bold)
                }
                Text("智能面试助手", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                Text(
                    "轻量用户版 · 文字对话驱动所有 Agent",
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        item {
            ElevatedCard(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(8.dp),
                colors = CardDefaults.elevatedCardColors(containerColor = Color.White)
            ) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(999.dp))
                            .background(AppBackground)
                            .padding(4.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        AuthSegment(
                            selected = viewModel.authMode == 0,
                            text = "登录",
                            modifier = Modifier.weight(1f),
                            onClick = { viewModel.switchAuthMode(0) }
                        )
                        AuthSegment(
                            selected = viewModel.authMode == 1,
                            text = "注册",
                            modifier = Modifier.weight(1f),
                            onClick = { viewModel.switchAuthMode(1) }
                        )
                    }

                    if (viewModel.authMode == 0) {
                        OutlinedTextField(
                            value = loginEmail,
                            onValueChange = { loginEmail = it },
                            label = { Text("邮箱") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                            modifier = Modifier.fillMaxWidth()
                        )
                        OutlinedTextField(
                            value = loginPassword,
                            onValueChange = { loginPassword = it },
                            label = { Text("密码") },
                            singleLine = true,
                            visualTransformation = PasswordVisualTransformation(),
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                            modifier = Modifier.fillMaxWidth()
                        )
                    } else {
                        OutlinedTextField(
                            value = registerName,
                            onValueChange = { registerName = it },
                            label = { Text("姓名") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                        OutlinedTextField(
                            value = registerEmail,
                            onValueChange = { registerEmail = it },
                            label = { Text("邮箱") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                            modifier = Modifier.fillMaxWidth()
                        )
                        OutlinedTextField(
                            value = registerPassword,
                            onValueChange = { registerPassword = it },
                            label = { Text("密码") },
                            singleLine = true,
                            visualTransformation = PasswordVisualTransformation(),
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    Button(
                        onClick = {
                            if (viewModel.authMode == 0) {
                                viewModel.login(loginEmail, loginPassword)
                            } else {
                                viewModel.register(registerName, registerEmail, registerPassword)
                            }
                        },
                        enabled = !viewModel.isLoading,
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(vertical = 13.dp)
                    ) {
                        if (viewModel.isLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(18.dp),
                                strokeWidth = 2.dp,
                                color = Color.White
                            )
                            Spacer(Modifier.width(10.dp))
                        }
                        Text(if (viewModel.authMode == 0) "登录" else "注册并登录")
                    }

                    viewModel.authError?.let {
                        Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                    Text(
                        "Token 会保存在本地，启动时自动调用后端校验登录状态。",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}

@Composable
private fun AuthSegment(selected: Boolean, text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Box(
        modifier = modifier
            .height(38.dp)
            .clip(RoundedCornerShape(999.dp))
            .background(if (selected) Color.White else Color.Transparent)
            .clickable(onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = text,
            color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium
        )
    }
}

@Composable
private fun MainShell(viewModel: HarmonyViewModel) {
    val tabs = listOf(
        BottomItem("首页", Icons.Filled.Home),
        BottomItem("助手", Icons.Filled.SmartToy),
        BottomItem("历史", Icons.Filled.History),
        BottomItem("我的", Icons.Filled.Person)
    )

    Scaffold(
        containerColor = AppBackground,
        bottomBar = {
            NavigationBar(containerColor = Color.White) {
                tabs.forEachIndexed { index, item ->
                    NavigationBarItem(
                        selected = viewModel.currentTab == index,
                        onClick = { viewModel.switchTab(index) },
                        icon = { Icon(item.icon, contentDescription = item.label) },
                        label = { Text(item.label) }
                    )
                }
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            when (viewModel.currentTab) {
                0 -> HomeScreen(viewModel)
                1 -> AssistantScreen(viewModel)
                2 -> HistoryScreen(viewModel)
                else -> ProfileScreen(viewModel)
            }
        }
    }
}

private data class BottomItem(val label: String, val icon: ImageVector)

@Composable
private fun HomeScreen(viewModel: HarmonyViewModel) {
    val gridState = rememberLazyGridState()
    LazyVerticalGrid(
        columns = GridCells.Adaptive(minSize = 154.dp),
        state = gridState,
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        fullWidthItem {
            TechHero(name = viewModel.user?.name ?: "同学")
        }
        fullWidthItem {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Agent 快捷入口", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                FilterChip(selected = true, onClick = {}, label = { Text("纯文字") })
            }
        }
        gridItems(AgentShortcuts, key = { it.key }) { shortcut ->
            ShortcutCard(shortcut = shortcut, onClick = { viewModel.openShortcut(shortcut) })
        }
        fullWidthItem {
            RecentPanel(
                records = viewModel.history.take(3),
                onOpenHistory = { viewModel.switchTab(2) },
                onSelect = { viewModel.selectHistory(it) }
            )
        }
    }
    HistoryDialog(viewModel)
}

private fun LazyGridScope.fullWidthItem(content: @Composable () -> Unit) {
    item(span = { GridItemSpan(maxLineSpan) }) {
        content()
    }
}

@Composable
private fun TechHero(name: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(176.dp)
            .clip(RoundedCornerShape(8.dp))
    ) {
        AnimatedTechCanvas(modifier = Modifier.fillMaxSize())
        Column(
            modifier = Modifier
                .align(Alignment.CenterStart)
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text("你好，$name", color = Color.White, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                "粘贴材料，后端 IntentRouter 会自动分发 Agent。",
                color = Color.White.copy(alpha = 0.78f),
                style = MaterialTheme.typography.bodyMedium
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                HeroTag("纯文字")
                HeroTag("统一入口")
                HeroTag("Agent 调度")
            }
        }
    }
}

@Composable
private fun AnimatedTechCanvas(modifier: Modifier = Modifier, compact: Boolean = false) {
    val transition = rememberInfiniteTransition(label = "tech-canvas")
    val sweep by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = if (compact) 3200 else 4200, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "scan"
    )
    val pulse by transition.animateFloat(
        initialValue = 0.35f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1400, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    Canvas(modifier = modifier) {
        drawRect(
            brush = Brush.linearGradient(
                colors = listOf(Color(0xFF06121F), Color(0xFF0F766E), Color(0xFF164E63)),
                start = Offset.Zero,
                end = Offset(size.width, size.height)
            )
        )

        val gridPaint = Color.White.copy(alpha = 0.10f)
        val accent = Color(0xFF67E8F9)
        for (i in 1..4) {
            val y = size.height * i / 5f
            drawLine(gridPaint, Offset(18f, y), Offset(size.width - 18f, y), strokeWidth = 1f)
        }
        for (i in 1..6) {
            val x = size.width * i / 7f
            drawLine(gridPaint, Offset(x, 14f), Offset(x, size.height - 14f), strokeWidth = 1f)
        }

        val path = Path().apply {
            moveTo(26f, size.height * 0.68f)
            lineTo(size.width * 0.28f, size.height * 0.40f)
            lineTo(size.width * 0.54f, size.height * 0.56f)
            lineTo(size.width * 0.78f, size.height * 0.30f)
            lineTo(size.width - 28f, size.height * 0.45f)
        }
        drawPath(path, Color.White.copy(alpha = 0.34f), style = Stroke(width = 3f))

        val scanX = size.width * sweep
        drawLine(accent.copy(alpha = 0.78f), Offset(scanX, 0f), Offset(scanX, size.height), strokeWidth = 3f)
        drawLine(accent.copy(alpha = 0.18f), Offset(scanX - 16f, 0f), Offset(scanX - 16f, size.height), strokeWidth = 10f)

        val nodes = listOf(
            Offset(size.width * 0.28f, size.height * 0.40f),
            Offset(size.width * 0.54f, size.height * 0.56f),
            Offset(size.width * 0.78f, size.height * 0.30f),
            Offset(size.width - 28f, size.height * 0.45f)
        )
        nodes.forEachIndexed { index, point ->
            val phase = ((pulse + index * 0.16f) % 1f)
            drawCircle(accent.copy(alpha = 0.14f * (1f - phase)), radius = 20f + 18f * phase, center = point)
            drawCircle(Color.White.copy(alpha = 0.88f), radius = 4f + 2f * pulse, center = point)
        }
    }
}

@Composable
private fun HeroTag(text: String) {
    Text(
        text = text,
        color = Color.White.copy(alpha = 0.88f),
        style = MaterialTheme.typography.labelMedium,
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(Color.White.copy(alpha = 0.14f))
            .padding(horizontal = 10.dp, vertical = 6.dp)
    )
}

@Composable
private fun ShortcutCard(shortcut: AgentShortcut, onClick: () -> Unit) {
    val color = colorFromHex(shortcut.colorHex)
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(142.dp)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = thinBorder()
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(color.copy(alpha = 0.12f)),
                    contentAlignment = Alignment.Center
                ) {
                    Text(shortcut.iconText, color = color, fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.weight(1f))
                AgentSignalGlyph(color)
            }
            Text(shortcut.title, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                shortcut.subtitle,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun AgentSignalGlyph(color: Color) {
    val transition = rememberInfiniteTransition(label = "agent-signal")
    val phase by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1800, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "phase"
    )
    Canvas(modifier = Modifier.size(width = 38.dp, height = 22.dp)) {
        val baseY = size.height * 0.72f
        for (i in 0..3) {
            val local = ((phase + i * 0.18f) % 1f)
            val height = size.height * (0.25f + 0.55f * local)
            val x = 4f + i * 9f
            drawLine(
                color = color.copy(alpha = 0.22f + 0.58f * local),
                start = Offset(x, baseY),
                end = Offset(x, baseY - height),
                strokeWidth = 4f
            )
        }
    }
}

@Composable
private fun RecentPanel(records: List<HistoryRecord>, onOpenHistory: () -> Unit, onSelect: (HistoryRecord) -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = thinBorder()
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("最近记录", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                TextButton(onClick = onOpenHistory) { Text("查看全部") }
            }
            if (records.isEmpty()) {
                Text("暂无历史。生成内容后会保存在这里。", color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                records.forEach { record ->
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(8.dp))
                            .clickable { onSelect(record) }
                            .background(AppBackground)
                            .padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text(record.title, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(record.preview, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    }
                }
            }
        }
    }
}

@Composable
private fun AssistantScreen(viewModel: HarmonyViewModel) {
    val listState = rememberLazyListState()
    LaunchedEffect(viewModel.messages.size, viewModel.isSending) {
        if (viewModel.messages.isNotEmpty()) {
            listState.animateScrollToItem(viewModel.messages.lastIndex)
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        AssistantShortcutStrip(onShortcut = viewModel::openShortcut)
        HorizontalDivider(color = LineColor)
        MessageList(
            messages = viewModel.messages,
            isSending = viewModel.isSending,
            state = listState,
            modifier = Modifier.weight(1f)
        )
        HorizontalDivider(color = LineColor)
        Composer(
            draft = viewModel.draft,
            isSending = viewModel.isSending,
            onDraftChange = viewModel::updateDraft,
            onSend = viewModel::sendChat,
            onReset = viewModel::resetConversation
        )
    }
}

@Composable
private fun AssistantShortcutStrip(onShortcut: (AgentShortcut) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White)
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 12.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        AgentShortcuts.forEach { shortcut ->
            AssistChip(
                onClick = { onShortcut(shortcut) },
                label = { Text(shortcut.title) },
                leadingIcon = {
                    Text(shortcut.iconText, color = colorFromHex(shortcut.colorHex), fontWeight = FontWeight.Bold)
                }
            )
        }
    }
}

@Composable
private fun MessageList(
    messages: List<ChatMessage>,
    isSending: Boolean,
    state: LazyListState,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier
            .fillMaxWidth()
            .background(AppBackground),
        state = state,
        contentPadding = PaddingValues(14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        items(messages, key = { it.id }) { message ->
            ChatBubble(message)
        }
        if (isSending) {
            item {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    Text("生成中", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun ChatBubble(message: ChatMessage) {
    val isUser = message.role == ChatRole.User
    Box(modifier = Modifier.fillMaxWidth()) {
        Surface(
            modifier = Modifier
                .align(if (isUser) Alignment.CenterEnd else Alignment.CenterStart)
                .fillMaxWidth(0.86f),
            shape = RoundedCornerShape(8.dp),
            color = if (isUser) MaterialTheme.colorScheme.primary else Color.White,
            border = if (isUser) null else thinBorder()
        ) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                SelectionContainer {
                    Text(
                        message.text,
                        color = if (isUser) Color.White else MaterialTheme.colorScheme.onSurface,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
                Text(
                    message.createdAt,
                    color = if (isUser) Color.White.copy(alpha = 0.72f) else MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.labelSmall
                )
            }
        }
    }
}

@Composable
private fun Composer(
    draft: String,
    isSending: Boolean,
    onDraftChange: (String) -> Unit,
    onSend: () -> Unit,
    onReset: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White)
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        OutlinedTextField(
            value = draft,
            onValueChange = onDraftChange,
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 108.dp, max = 180.dp),
            placeholder = { Text("粘贴简历、JD、项目经历、面试回答或 Offer 信息") },
            minLines = 4,
            maxLines = 7
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("${draft.length} 字", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.weight(1f))
            IconButton(onClick = onReset, enabled = !isSending) {
                Icon(Icons.Filled.Delete, contentDescription = "清空对话")
            }
            Button(
                onClick = onSend,
                enabled = !isSending && draft.trim().isNotEmpty()
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("发送")
            }
        }
    }
}

@Composable
private fun HistoryScreen(viewModel: HarmonyViewModel) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("历史记录", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Spacer(Modifier.weight(1f))
                TextButton(onClick = viewModel::clearHistory, enabled = viewModel.history.isNotEmpty()) {
                    Text("清空")
                }
            }
        }
        if (viewModel.history.isEmpty()) {
            item {
                EmptyState(
                    title = "暂无历史",
                    message = "助手生成的报告和对话会按本地历史保存。"
                )
            }
        } else {
            items(viewModel.history, key = { it.id }) { record ->
                HistoryCard(
                    record = record,
                    onClick = { viewModel.selectHistory(record) },
                    onDelete = { viewModel.deleteHistory(record) }
                )
            }
        }
    }
    HistoryDialog(viewModel)
}

@Composable
private fun HistoryCard(record: HistoryRecord, onClick: () -> Unit, onDelete: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = thinBorder()
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.Top
        ) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(record.title, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Spacer(Modifier.width(8.dp))
                    Text(
                        intentLabel(record.intent),
                        color = MaterialTheme.colorScheme.primary,
                        style = MaterialTheme.typography.labelSmall,
                        modifier = Modifier
                            .clip(RoundedCornerShape(999.dp))
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f))
                            .padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
                Text(record.preview, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(record.createdAt, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelSmall)
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Filled.Delete, contentDescription = "删除记录")
            }
        }
    }
}

@Composable
private fun HistoryDialog(viewModel: HarmonyViewModel) {
    val record = viewModel.selectedHistory ?: return
    AlertDialog(
        onDismissRequest = { viewModel.selectHistory(null) },
        confirmButton = {
            TextButton(onClick = { viewModel.selectHistory(null) }) { Text("关闭") }
        },
        dismissButton = {
            TextButton(onClick = { viewModel.deleteHistory(record) }) { Text("删除") }
        },
        title = { Text(record.title, maxLines = 2, overflow = TextOverflow.Ellipsis) },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(max = 520.dp)
                    .wrapContentHeight()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                DetailBlock(title = "用户输入", text = record.userMessage)
                DetailBlock(title = "输出结果", text = record.resultText.ifBlank { record.assistantMessage })
                if (record.rawJson.isNotBlank()) {
                    DetailBlock(title = "原始 JSON", text = record.rawJson)
                }
            }
        }
    )
}

@Composable
private fun DetailBlock(title: String, text: String) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, fontWeight = FontWeight.Bold)
        SelectionContainer {
            Text(text.ifBlank { "无" }, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun ProfileScreen(viewModel: HarmonyViewModel) {
    var showLogout by remember { mutableStateOf(false) }
    var showClear by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            ProfileHeader(name = viewModel.user?.name ?: "用户", email = viewModel.user?.email.orEmpty())
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                MetricTile("历史记录", "${viewModel.history.size}", "本地保存", Modifier.weight(1f))
                MetricTile("Token", if (viewModel.token.isBlank()) "未保存" else "已保存", "本地存储", Modifier.weight(1f))
            }
        }
        item {
            SettingsCard {
                SettingsRow(title = "自动保存历史", icon = Icons.Filled.History) {
                    Switch(
                        checked = viewModel.autoSaveHistory,
                        onCheckedChange = viewModel::toggleAutoSaveHistory
                    )
                }
                HorizontalDivider(color = LineColor)
                SettingsRow(title = "账号状态", icon = Icons.Filled.CheckCircle) {
                    Text(viewModel.user?.status ?: "unknown", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                HorizontalDivider(color = LineColor)
                SettingsRow(title = "角色", icon = Icons.Filled.Person) {
                    Text(viewModel.user?.role ?: "user", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        item {
            SettingsCard {
                Button(
                    onClick = { viewModel.validateToken() },
                    enabled = !viewModel.isLoading,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
                ) {
                    Icon(Icons.Filled.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(if (viewModel.isLoading) "校验中" else "校验登录")
                }
                if (viewModel.statusMessage.isNotBlank()) {
                    Text(viewModel.statusMessage, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(
                    onClick = { showClear = true },
                    enabled = viewModel.history.isNotEmpty(),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Filled.Delete, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("清空历史")
                }
                Button(
                    onClick = { showLogout = true },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("退出登录")
                }
            }
        }
    }

    if (showLogout) {
        ConfirmDialog(
            title = "退出登录",
            message = "退出后会清除本地 Token，需要重新登录。",
            confirmText = "退出",
            onConfirm = {
                showLogout = false
                viewModel.logout()
            },
            onDismiss = { showLogout = false }
        )
    }
    if (showClear) {
        ConfirmDialog(
            title = "清空历史",
            message = "本地保存的报告和对话记录会被删除。",
            confirmText = "清空",
            onConfirm = {
                showClear = false
                viewModel.clearHistory()
            },
            onDismiss = { showClear = false }
        )
    }
}

@Composable
private fun ProfileHeader(name: String, email: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(156.dp)
            .clip(RoundedCornerShape(8.dp))
    ) {
        AnimatedTechCanvas(modifier = Modifier.fillMaxSize(), compact = true)
        Row(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(18.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(58.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color.White.copy(alpha = 0.16f)),
                contentAlignment = Alignment.Center
            ) {
                Text(name.firstOrNull()?.toString() ?: "U", color = Color.White, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.width(14.dp))
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text(name, color = Color.White, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(email, color = Color.White.copy(alpha = 0.78f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("智能面试助手账号", color = Color.White.copy(alpha = 0.72f), style = MaterialTheme.typography.labelMedium)
            }
        }
    }
}

@Composable
private fun MetricTile(title: String, value: String, caption: String, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = thinBorder()
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelMedium)
            Text(value, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, maxLines = 1)
            Text(caption, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelSmall)
        }
    }
}

@Composable
private fun SettingsCard(content: @Composable ColumnScope.() -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = thinBorder()
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            content = content
        )
    }
}

@Composable
private fun SettingsRow(title: String, icon: ImageVector, accessory: @Composable () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
        }
        Spacer(Modifier.width(12.dp))
        Text(title)
        Spacer(Modifier.weight(1f))
        accessory()
    }
}

@Composable
private fun EmptyState(title: String, message: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = thinBorder()
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(46.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Filled.SmartToy, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            }
            Text(title, fontWeight = FontWeight.Bold)
            Text(message, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun ConfirmDialog(
    title: String,
    message: String,
    confirmText: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { Text(message) },
        confirmButton = {
            TextButton(onClick = onConfirm) { Text(confirmText, color = MaterialTheme.colorScheme.error) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("取消") }
        }
    )
}

private fun colorFromHex(hex: String): Color =
    runCatching { Color(AndroidColor.parseColor(hex)) }.getOrDefault(Color(0xFF0F766E))

private fun thinBorder(): BorderStroke = BorderStroke(1.dp, LineColor)
