# set current folder and load packages and functions
current_folder <- dirname(rstudioapi::getSourceEditorContext()$path)
setwd(current_folder)
#setwd("../")
getwd()
options(scipen=9999)

# load common functions
source("commonFunctions.R")
library(scales)
library(ggbeeswarm)

########################
# data
test_data_file <- "tables/summary_table.tsv"
test_data <- fread(test_data_file, data.table = F)
replica_data_file <- "tables/task_table.tsv"
replica_data <- fread(replica_data_file, data.table = F)
task_data_file <- "tables/model_table.tsv"
task_data <- fread(task_data_file, data.table = F)
model_data_file <- "tables/benchmark_table.tsv"
model_data <- fread(model_data_file, data.table = F)

########################
# out files

pass_barplot_file <- "plots/average_pass_barplot.png"
pass_boxplot_file <- "plots/average_pass_boxplot.pdf"
valid_boxplot_file <- "plots/average_valid_boxplot.pdf"
error_barplot_file <- "plots/average_error_barplot.pdf"
error_boxplot_file <- "plots/average_error_boxplot.pdf"
at_least_one_error_barplot_file <- "plots/at_least_one_error_barplot.pdf"

difficulty_boxplot_file <- "plots/difficulty_boxplot.pdf"
difficulty_barplot_file <- "plots/difficulty_barplot.pdf"

fp_boxplot_file <- "plots/fp_boxplot.pdf"
fn_boxplot_file <- "plots/fn_boxplot.pdf"
fp_and_fn_post_boxplot_file  <- "plots/fp_and_fn_post_boxplot.pdf"

cc_barplot_file <- "plots/cc_barplot.pdf"

complexity_plot_file <- "plots/complexity_barplot.pdf"
complexity_pattern_plot_file<- "plots/complexity_pattern_barplot.pdf"

misclassified_barplot_file <- "plots/misclassified_barplot.pdf"

unsolved_tb_file <- "tables/unsolved_tasks.tsv"
solved_tb_file <- "tables/solved_tasks.tsv"

########################
# colors

# licence
licence_names <- c( "Yes","No")
names(licence_names) <- c("open","proprietary")
licence_col <- c("#a6bddb","#3690c0")
names(licence_col) <- licence_names

eval_col <- "#e7298a"

complexity_vals <- c("S", "Q", "QQ", "NQ")
complexity_colors <- c("#fee8c8","#fdbb84","#ef6548","#d7301f")
names(complexity_colors) <- complexity_vals

# cc_vals <- sort(unique(task_data$solution_cc), decreasing = F)

cc_vals <- c("Low","High")
colors_cc_vals <- c("#fee8c8","#d7301f")
#colors_cc_vals <- c("gray80","gray20")
names(colors_cc_vals) <- cc_vals

########################
# define orders
unique(model_data$cond)
cond_names <- c("Pre","Post")
names(cond_names) <- c("pre","post")
model_data$Cond <- cond_names[model_data$cond]
model_data$Cond <- factor(model_data$Cond, levels = cond_names)

# Rename tasks
replica_data$task <- gsub("HE","HEx",replica_data$task)
task_data$task <- gsub("HE","HEx",task_data$task)
test_data$task <- gsub("HE","HEx",test_data$task)

models_order <-  model_data[which(model_data$cond == "pre"),"Short name"][order(model_data[which(model_data$cond == "post"),"avg_Pass"], decreasing = T)]
model_data$Model <- factor(model_data$`Short name`, levels = models_order)

model_data$`Open model` <- licence_names[model_data$Licence]
model_data$`Open model` <- factor(model_data$Open,levels = licence_names )

task_data$Cond <- cond_names[task_data$cond]
task_data$Cond <- factor(task_data$Cond, levels = cond_names)
task_data$Model <- factor(task_data$`Short name`, levels = models_order)
task_data$`Open model` <- licence_names[task_data$Licence]
task_data$`Open model` <- factor(task_data$Open,levels = licence_names )

task_data[,"Difficulty"] <- factor(task_data$solution_human_comp, levels = complexity_vals)

CC_limit <- 5
task_data$CC_prog <- NA
task_data$CC_prog[which(task_data$prog_cc >  CC_limit)] <- "High"
task_data$CC_prog[which(task_data$prog_cc <= CC_limit)] <- "Low"
task_data$CC_prog <-factor(task_data$CC_prog, levels = cc_vals)

task_data$CC_sol <- NA
task_data$CC_sol[which(task_data$solution_cc >  CC_limit)] <- "High"
task_data$CC_sol[which(task_data$solution_cc <= CC_limit)] <- "Low"
task_data$CC_sol <-factor(task_data$CC_sol, levels = cc_vals)

task_data_post <- task_data[which(task_data$cond == "post"),]
task_data_pre <- task_data[which(task_data$cond == "pre"),]

# detailed data
replica_data$Model <- factor(replica_data$`Short name`, levels = models_order)


length(unique(test_data$test))

################################################
# Outlier
# which(table(task_data_post[which(task_data_post$n_valid == 0),c("n_valid","task")]) > 23)
# tasks_to_check <- c("HE1", "HE158","HE21")



########################
# boxplot mean Pass and pass@1
pass_boxplot <- ggplot(task_data, aes(x = Model, y = avg_p_Pass, fill = `Open model`)) +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5) +
  geom_point(data = model_data, aes( y=avg_evalAt1), shape = 8, color=eval_col, size = 1, show.legend = F) +
  #facet_wrap(~Cond) +
  facet_wrap(~Cond, ncol=1) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  ylab("Mean Pass Tests per Task")
pass_boxplot
ggsave(filename = pass_boxplot_file, plot = pass_boxplot, device = "pdf", width = 3.5, height = 4, units = "in", dpi = 300 )



########################
# boxplot fraction valid (100% pass tests) i.e. Eval@1
valid_boxplot <- 
  ggplot(task_data, aes(x = Model, y = p_valid, fill = `Open model`)) +
  #geom_quasirandom(method = "smiley") +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5, outliers = F) +
  geom_jitter(position=position_jitter(0.2), colour = "gray20", size = 0.4, alpha = 0.6, shape = 16) +
  geom_point(data = model_data, aes( y=avg_evalAt1), shape = 8, color=eval_col, size = 0.2, show.legend = F) +
  #facet_wrap(~Cond) +
  facet_wrap(~Cond, ncol=1) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  ylab("Eval@1 per Task")
valid_boxplot


ggsave(filename = valid_boxplot_file, plot = valid_boxplot, device = "pdf", width = 3.5, height = 4, units = "in", dpi = 300 )



########################
# boxplot mean Error

error_boxplot <- ggplot(task_data_post, aes(x = Model, y = avg_p_Error, fill = `Open model`)) +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5) +
  #facet_wrap(~Cond, ncol=1) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-1, units = "pt")  ) +
  ylab("Mean Tests Errors per Task")
error_boxplot
ggsave(filename = error_boxplot_file, plot = error_boxplot, device = "pdf", width = 3.5, height = 2, units = "in", dpi = 300 )

########################
# divide by complexity
colnames(task_data)
difficulty_boxplot <- ggplot(task_data_post, aes(x=Model, y = avg_p_Pass, fill =  `Difficulty`)) +
  geom_boxplot(colour="gray60", linewidth = 0.2, outlier.size = 0.3) +
  scale_fill_manual(values = complexity_colors) +
  scale_y_continuous(labels = percent) +
  theme_se() +
  ylab("Mean Pass Tests per Post Task") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-1, units = "pt")  ) 
difficulty_boxplot

ggsave(filename = difficulty_boxplot_file, plot = difficulty_boxplot, device = "pdf", width = 3.5, height = 2.25, units = "in", dpi = 300 )


########################
# barplot number of solved tasks

task_solved <- task_data[which(task_data$n_valid >0),]
fwrite(task_solved,file = solved_tb_file, sep = "\t",row.names = F, col.names = T)

#task_solved <- task_data_post[which(task_data_post$n_valid >0),]
#task_solved_NQ <- task_solved[which(task_solved$Difficulty == "NQ"),]

ggplot(task_solved, aes(x=task, fill=`Open model`)) +
  geom_bar(stat = 'count') +
  ylab("Number of models with Eval@1 > 0") #+
  #facet_wrap(cond~solution_human_comp, scales = "free_x", ncol=2)

ggplot(task_solved, aes(x=Model, fill=Difficulty)) +
  geom_bar(stat='count') +
  scale_fill_manual(values = complexity_colors) +
  ylab("Number of models with accept@1 > 0")

ggplot(task_solved, aes(x=Model, fill=CC_sol)) +
  geom_bar(stat='count') +
  ylab("Number of models with accept@1 > 0")


########################
# barplot number of not solved task


task_unsolved <- task_data_post[which(task_data_post$n_valid ==0),]

unsolved_tb <- data.frame(row.names = unique(task_data$task))
unsolved_tb$task <- rownames(unsolved_tb)
#tid <- "HE1"
unsolved_tb$n_unsolved <- sapply(X = unsolved_tb$task,  function(tid){
  ttb <- task_data[which(task_data$task == tid & task_data$cond == 'post' & task_data$n_valid == 0),]
  length(unique(ttb$model))
})
unsolved_tb$complexity <- sapply(X = unsolved_tb$task,  function(tid){
  ttb <- task_data[which(task_data$task == tid & task_data$cond == 'post' & task_data$n_valid == 0),]
  ttb$Difficulty[1]
})
unsolved_tb$cc <- sapply(X = unsolved_tb$task,  function(tid){
   ttb <- task_data[which(task_data$task == tid & task_data$cond == 'post' & task_data$n_valid == 0),]
   unique(ttb$CC_sol)
 })


unsolved_tb <- unsolved_tb[order(unsolved_tb$n_unsolved, decreasing = T),]
fwrite(unsolved_tb, unsolved_tb_file, quote = F, sep = "\t", row.names = F, col.names = T)

#unsolved_tb$task <- gsub("HE","",unsolved_tb$task)
unsolved_tb$Task <- factor(unsolved_tb$task, levels = unsolved_tb$task)
unsolved_tb$Difficulty  <- factor(unsolved_tb$complexity , levels = complexity_vals)
#unsolved_tb$CC  <- factor(unsolved_tb$cc , levels = cc_vals)


difficulty_barplot <-  ggplot(data = unsolved_tb, aes(x=Task, y=n_unsolved, fill=Difficulty)) +
  geom_bar(stat = 'identity') +
  scale_fill_manual(values = complexity_colors) +
  theme_se() +
  ylab("Number of Models (total 24)") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank(), axis.text.x.bottom = element_text(size = 4)) +
  theme(legend.position = "top", legend.box.spacing = unit(-1, units = "pt")  ) +
  scale_y_continuous(breaks=c(0,6,12,18,24), labels=c(0,6,12,18,24)) +
  theme(panel.grid.major.x = element_line(linewidth=0.1, colour = "gray90"))

difficulty_barplot
ggsave(filename = difficulty_barplot_file, plot = difficulty_barplot, device = "pdf", width = 3.5, height = 1.8, units = "in", dpi = 300 )

#barplot(1:11, col=rev(terrain.colors(11)))
library(ggpattern)


cc_barplot <- ggplot(data = unsolved_tb, aes(x=Task, y=n_unsolved, fill=cc)) +
#  geom_bar(stat = 'identity') +
  geom_col_pattern(aes( pattern_angle=cc),   pattern_density = 0.05, pattern_colour = "gray60", pattern_size = 0.1, pattern_spacing =0.05) +
  scale_pattern_angle_manual(values = c(45,-45)) +
  theme_se() +
  scale_fill_manual(values = colors_cc_vals) +
  scale_pattern_type_manual(values = c("hexagonal", "rhombille")) + 
  #scale_fill_manual(values = rev(hcl.colors(length(cc_vals), palette = "Reds"))) +
  ylab("Number of Models (total 24)") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank(), axis.text.x.bottom = element_text(size = 4)) +
  theme(legend.position = "top", legend.box.spacing = unit(-1, units = "pt"),legend.box = "horizontal"  ) +
  scale_y_continuous(breaks=c(0,6,12,18,24), labels=c(0,6,12,18,24))  +
  guides(fill=guide_legend(nrow=1,byrow=TRUE,title = "Cyclomatic Complexity"), pattern_angle = 'none')+
  theme(panel.grid.major.x = element_line(linewidth=0.1, colour = "gray90"))
cc_barplot
ggsave(filename = cc_barplot_file, plot = cc_barplot, device = "pdf", width = 3.5, height = 1.8, units = "in", dpi = 300 )


######## 
# difficulty and cc in a single barplot
difficulty_barplot_comb <-  ggplot(data = unsolved_tb, aes(x=Task, y=n_unsolved, fill=Difficulty)) +
  geom_bar(stat = 'identity',linewidth = 0) +
  scale_fill_manual(values = complexity_colors) +
  #scale_color_manual(values = c("gray80","gray40")) +
  theme_se() +
  ylab("Number of Models (total 24)") +
  #theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank(), axis.text.x.bottom = element_text(size = 4)) +
  theme(axis.text.x = element_blank(), axis.title.x = element_blank()) +
  #theme(legend.position = "top", legend.box.spacing = unit(-1, units = "pt")  ) +
  scale_y_continuous(breaks=c(0,6,12,18,24), labels=c(0,6,12,18,24)) +
  theme(panel.grid.major.x = element_line(linewidth=0.1, colour = "gray90")) +
  theme(plot.margin = unit(c(0, 2, 0, 2),"mm")) +
  theme(legend.position = "top", legend.title = element_text(size = 5), legend.text = element_text(size = 4), legend.key.height = unit(2, "mm"), legend.key.width = unit(1,"mm") )  
difficulty_barplot_comb

cc_barplot_comb <- ggplot(data = unsolved_tb, aes(x=Task, y=1, fill=cc)) +
  geom_col() +
  scale_fill_manual(values = c("gray80","gray40")) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank(), axis.text.x.bottom = element_text(size = 4)) +
  theme(axis.title.y = element_blank(), axis.text.y = element_blank()) +
  theme(panel.grid.major = element_blank()) +
  theme(plot.margin = unit(c(0, 2, 1, 2),"mm")) +
  #theme(legend.position = "top", legend.box.spacing = unit(-1, units = "pt"),   )  +
  guides(fill=guide_legend(nrow=1,byrow=TRUE,title = "Cyclomatic Complexity")) +
  theme(legend.position = "top", legend.title = element_text(size = 5), legend.text = element_text(size = 4), legend.key.height = unit(2, "mm"), legend.key.width = unit(1,"mm") )  
cc_barplot_comb

difficulty_barplot_comb_leg <- get_legend(difficulty_barplot_comb)
cc_barplot_comb_leg <- get_legend(cc_barplot_comb)


complexity_plot <- ggarrange(
  ggarrange(difficulty_barplot_comb_leg,  cc_barplot_comb_leg ),
  ggarrange(difficulty_barplot_comb+theme(legend.position = "none"), 
          cc_barplot_comb+theme(legend.position = "none"), 
          ncol = 1 ,heights = c(0.83,0.17), align="v"),
  ncol = 1 ,heights = c(0.05,0.95))
complexity_plot

ggsave(filename = complexity_plot_file, plot = complexity_plot, device = "pdf", width = 3.5, height = 2, units = "in", dpi = 300 )

######## 
# difficulty and cc in a single barplot using different texture

library(ggpattern)
unsolved_tb$Difficulty
complexity_pattern_plot <- ggplot(data = unsolved_tb, aes(x=Task, y=n_unsolved )) +
  geom_bar_pattern(aes( pattern_angle =  cc, fill = Difficulty ), stat = "identity",
                   pattern_density = 0.05, 
                   pattern_colour = "gray80", pattern_size = 0.1, pattern_spacing =0.02,
                   pattern = "stripe"
                   ) +
  scale_fill_manual(values = complexity_colors) +
  scale_pattern_angle_manual(values = c("Low" = 60, "High" = -60)) +
  theme_se() +
  ylab("Number of Models (total 24)") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank(), axis.text.x.bottom = element_text(size = 4)) +
  theme(panel.grid.major.x =  element_line(linewidth = 0.1)) +
  guides(pattern_angle=guide_legend(nrow=1,byrow=TRUE,title = "Cyclomatic Complexity")) +
  theme(legend.position = "top", legend.title = element_text(size = 5), legend.text = element_text(size = 4),legend.key.width = unit(4,"mm") )  
  

complexity_pattern_plot

ggsave(filename = complexity_pattern_plot_file, plot = complexity_pattern_plot, device = "pdf", width = 3.5, height = 2, units = "in", dpi = 300 )


########################
# count statically detectable errors

at_least_one_error_plot <- ggplot(task_data, aes(x=Model, y=n_at_least_one_error, fill=`Open model`)) +
  geom_boxplot(outliers = T, colour="gray60", linewidth = 0.2, outlier.color = "gray60", outlier.size = 0.5) +
  #geom_jitter( color="gray80", size = 0.5, alpha = 0.8, width = 0.2, shape = 16, height = 0.1) +
  #facet_wrap(~Cond, ncol=1) +
  scale_fill_manual(values = licence_col) +
  theme_se() +
  ylab("Replicas with an Error test") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) + #, axis.text.x.bottom = element_text(size = 4)) +
  theme(legend.position = "top",legend.box.spacing = unit(-1, units = "pt"),legend.box = "horizontal") +
  scale_y_continuous(breaks=c(0,2,4,6,8,10), labels=c(0,2,4,6,8,10),limits = c(0,10) ) 

at_least_one_error_plot


ggsave(filename = at_least_one_error_barplot_file, plot = at_least_one_error_plot, device = "pdf", width = 3.5, height = 2.25, units = "in", dpi = 300 )

###########################
# FP and FN

# top FP
fp_data <- task_data[order(task_data$avg_p_FP, decreasing = T),]

fp_case_1 <- test_data[which(test_data$model == fp_data$model[1] & test_data$task == fp_data$task[1] & test_data$cond == fp_data$cond[1]),]
fp_case_1 <- fp_case_1[which(fp_case_1$class == "FP"),]
fp_case_1_top <- fp_case_1[which(fp_case_1$test %in% names(sort(table(fp_case_1$test),decreasing = T)[1:3])),]
unique(fp_case_1_top$test)
fp_case_1_top$replica[which(fp_case_1_top$test == unique(fp_case_1_top$test)[2])]

fp_case_2 <- test_data[which(test_data$model == fp_data$model[2] & test_data$task == fp_data$task[2] & test_data$cond == fp_data$cond[2]),]
fp_case_2 <- fp_case_2[which(fp_case_2$class == "FP"),]
fp_case_2_top <- fp_case_2[which(fp_case_2$test %in% names(sort(table(fp_case_2$test),decreasing = T)[1:3])),]

fp_case_3 <- test_data[which(test_data$model == fp_data$model[3] & test_data$task == fp_data$task[3] & test_data$cond == fp_data$cond[3]),]
fp_case_3 <- fp_case_3[which(fp_case_3$class == "FP"),]
fp_case_3_top <- fp_case_3[which(fp_case_3$test %in% names(sort(table(fp_case_3$test),decreasing = T)[1:3])),]

# boxplot
fp_boxplot <- ggplot(task_data, aes(x=Model, y=avg_p_FP, fill = `Open model`)) +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5, outliers = F) +
  geom_jitter(position=position_jitter(0.2), colour = "gray20", size = 0.4, alpha = 0.6, shape = 16) +
  #geom_point(data = model_data, aes( y=avg_evalAt1), shape = 8, color=eval_col, size = 0.2, show.legend = F) +
  facet_wrap(~Cond, ncol=1) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  ylab("False Positive")
fp_boxplot
ggsave(filename = fp_boxplot_file, plot = fp_boxplot, device = "pdf", width = 3.5, height = 5, units = "in", dpi = 300 )



# top FN
fn_data <- task_data[order(task_data$avg_p_FN, decreasing = T),]

fn_case_1 <- test_data[which(test_data$model == fn_data$model[1] & test_data$task == fn_data$task[1] & test_data$cond == fn_data$cond[1]),]
fn_case_1 <- fn_case_1[which(fn_case_1$class == "FN"),]
fn_case_1_top <- fn_case_1[which(fn_case_1$test %in% names(sort(table(fn_case_1$test),decreasing = T)[1:3])),]

fn_case_2 <- test_data[which(test_data$model == fn_data$model[2] & test_data$task == fn_data$task[2] & test_data$cond == fn_data$cond[2]),]
fn_case_2 <- fn_case_2[which(fn_case_2$class == "FN"),]
fn_case_2_top <- fn_case_2[which(fn_case_2$test %in% names(sort(table(fn_case_2$test),decreasing = T)[1:3])),]

fn_case_3 <- test_data[which(test_data$model == fn_data$model[3] & test_data$task == fn_data$task[3] & test_data$cond == fn_data$cond[3]),]
fn_case_3 <- fn_case_3[which(fn_case_3$class == "FN"),]
fn_case_3_top <- fn_case_3[which(fn_case_3$test %in% names(sort(table(fn_case_3$test),decreasing = T)[1:3])),]


# boxplot
fn_boxplot <- ggplot(task_data, aes(x=Model, y=avg_p_FN, fill = `Open model`)) +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5, outliers = F) +
  geom_jitter(position=position_jitter(0.2), colour = "gray20", size = 0.4, alpha = 0.6, shape = 16) +
  #geom_point(data = model_data, aes( y=avg_evalAt1), shape = 8, color=eval_col, size = 0.2, show.legend = F) +
  facet_wrap(~Cond, ncol=1) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  ylab("False Negative")
fn_boxplot
ggsave(filename = fn_boxplot_file, plot = fn_boxplot, device = "pdf", width = 3.5, height = 5, units = "in", dpi = 300 )

unique(task_data$model)
task_data[which(task_data$task == "HEx57" & task_data$model == "claude-3-7-sonnet"),]


### boxplot false positive and false negative for post

# FP post 
fp_post__boxplot <- ggplot(task_data_post, aes(x=Model, y=avg_p_FP, fill = `Open model`)) +
  geom_jitter(position=position_jitter(0.2), colour = "gray20", size = 0.4, alpha = 0.6, shape = 16) +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5, outliers = F) +
  #geom_point(data = model_data, aes( y=avg_evalAt1), shape = 8, color=eval_col, size = 0.2, show.legend = F) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent, breaks=c(0,0.2,0.4), limits = c(0,0.4)) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  ylab("False Positive") 
fp_post__boxplot 

fn_post__boxplot <- ggplot(task_data_post, aes(x=Model, y=avg_p_FN, fill = `Open model`)) +
  geom_jitter(position=position_jitter(0.2), colour = "gray20", size = 0.4, alpha = 0.6, shape = 16) +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5, outliers = F) +
  #geom_point(data = model_data, aes( y=avg_evalAt1), shape = 8, color=eval_col, size = 0.2, show.legend = F) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent, breaks=c(0,0.2,0.4,0.6,0.8), limits = c(0,0.8)) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  ylab("False Negative")
fn_post__boxplot 

library(ggpubr)
fp_and_fn_post_boxplot <- ggarrange(fp_post__boxplot+ rremove("x.text"), fn_post__boxplot, ncol = 1 ,heights = c(0.33,0.67),
          common.legend = TRUE, legend = "top")
fp_and_fn_post_boxplot

ggsave(filename = fp_and_fn_post_boxplot_file, plot = fp_and_fn_post_boxplot, device = "pdf", width = 3.5, height = 3.5, units = "in", dpi = 300 )


###########################
# Impact of automatic generated tests

# library(reshape2)
# colnames(task_data)
# aa<-melt(task_data, id.vars = c("task","model","cond"), measure.vars = c("n_valid","n_valid_manual"))
# 
# ggplot(aa, aes(x=model, y=value, fill = variable)) +
#   geom_boxplot(colour="gray60", linewidth = 0.2, outlier.size = 0.3) +
#   facet_wrap(~cond)
model_data <- model_data[order(model_data$tot_Misclassified, decreasing = T),]

misclassified_barplot <- ggplot(model_data[which(model_data$cond == "post"),], aes(x=Model, y=tot_Misclassified/tot_ManualValid, fill = `Open model`)) +
  geom_bar(stat = 'identity') +
  scale_fill_manual(values = licence_col) +
  theme_se() +
  scale_y_continuous(labels = percent, breaks=c(0,0.1,0.2,0.3)) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  theme(panel.grid.major.x =  element_line(linewidth=0.1, colour = "gray90")) +
  ylab("Misclassified Solutions")
misclassified_barplot
ggsave(filename = misclassified_barplot_file, plot = misclassified_barplot, device = "pdf", width = 3.5, height = 1.9, units = "in", dpi = 300 )


model_data[which(model_data$tot_ManualValid == 0),]

# ggplot(task_data, aes(x=Model, y=(n_valid_manual-n_valid )/n_valid_manual, fill = task )) +
#   geom_bar(stat = 'identity') +
#   theme_se() +
#   theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
#   theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
#   ylab("Misclassified Solutions")




################################################################################################################################################
################################################################################################################################################
########################
######################## Tests and experiments
########################
################################################################################################################################################
################################################################################################################################################


########################
# count statically detectable errors
# library(reshape2)
# task_data_long <- melt(task_data, id.vars = c("task","Model","cond"), measure.vars = c("n_all_error","n_at_least_one_error"))
# 
# ggplot(task_data_long, aes(x=Model, y=value,color=variable)) +
# #  geom_jitter(position = position_jitter(0.9)) +
#   geom_boxplot() +
#   theme_se() +
#   theme(legend.position = "top") 

## save for internal use
# at_least_one_plot <- ggplot(task_data, aes(x=Model, y=n_at_least_one_error)) +
#   geom_boxplot(outliers = F, outlier.colour = "red") +
#   geom_jitter(position = position_jitter(0.2), color="gray60", size = 0.5, alpha = 0.8) +
#   theme_se() +
#   theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank(), axis.text.x.bottom = element_text(size = 4)) +
#   theme(legend.position = "top") +
#   scale_y_continuous(breaks=c(0,2,4,6,8,10), labels=c(0,2,4,6,8,10))  
# ggsave(filename = "plots/raw_at_least_one_plot.pdf", plot = at_least_one_plot, device = "pdf", width = 7.5, height = 4, units = "in", dpi = 300 )
# 
# all_error_plot <- ggplot(task_data, aes(x=Model, y=n_all_error)) +
#   geom_boxplot(outliers = F, outlier.colour = "red") +
#   geom_jitter(position = position_jitter(0.2), color="gray60", size = 0.5, alpha = 0.8) +
#   theme_se() +
#   theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank(), axis.text.x.bottom = element_text(size = 4)) +
#   theme(legend.position = "top") 
# ggsave(filename = "plots/raw_all_error_plot.pdf", plot = all_error_plot, device = "pdf", width = 7.5, height = 4, units = "in", dpi = 300 )

# compute outliers



ggplot(task_data_post, aes(x=Model, y = avg_p_Pass, fill =  `CC_prog`)) +
  geom_boxplot(colour="gray60", linewidth = 0.5, outlier.size = 0.5) +
  #theme_se() +
  ylab("Mean Pass Tests per Post Task") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-1, units = "pt")  ) 


ggplot(task_data_post, aes(x=Model, y = avg_p_Pass, fill =  `CC_sol`)) +
  geom_boxplot(colour="gray60", linewidth = 0.5, outlier.size = 0.5) +
  theme_se() +
  ylab("Mean Pass Tests per Post Task") +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-1, units = "pt")  ) 




########################
# specific task
task_id = "HEx21"

task_id <- tasks_to_check[2]
task_replica_data <- replica_data[which(replica_data$task == task_id & replica_data$cond == 'post'),]

ggplot(task_replica_data, aes(x=Model, y = p_Pass)) +
  geom_boxplot(colour="gray80", outliers = FALSE) +
  geom_jitter(color="gray20", size=1, alpha=0.9) + 
  scale_y_continuous(labels = percent) +
  theme_se() + labs(title = task_id) +
  ylab("Fraction of pass test in a replica") + 
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) 


########################
########################
########################
# checks that can be removed
ggplot(task_data, aes(x=model, y=avg_p_Pass)) +
  geom_boxplot() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank())

task_data_pre <- task_data[which(task_data$cond == "pre"),]
by(task_data_pre, INDICES = task_data_pre$model, function(X){mean(X$evalAt1)})


unsolved <- task_data_post[which(task_data_post$n_valid ==0),]
sort(table(unsolved$task))



which(task_data_post$evalAt1 != task_data_post$p_valid_manual)


ggplot(task_data, aes(x = Model, y = avg_p_FP, fill = `Open model`)) +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5) +
  #facet_wrap(~Cond) +
  facet_wrap(~Cond, ncol=1) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  ylab("Mean False Positive Tests per Task")

ggplot(task_data, aes(x = Model, y = avg_p_FN, fill = `Open model`)) +
  geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5) +
  #facet_wrap(~Cond) +
  facet_wrap(~Cond, ncol=1) +
  scale_fill_manual(values = licence_col) +
  scale_y_continuous(labels = percent) +
  theme_se() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
  theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
  ylab("Mean False Negative Tests per Task")



################################################
# barplot mean Pass and pass@1

# pass_barplot <- ggplot(model_data, aes(x = Model, y = avg_Pass, fill = `Open model` )) +
#   geom_bar(stat = "identity") +
#   geom_errorbar(aes(ymin=pmax(0,avg_Pass-sd_Pass), ymax=pmin(1,avg_Pass+sd_Pass)), width=.2,linewidth = 0.3,position=position_dodge(.9), color = "gray50") +
#   #geom_errorbar(aes(ymin=min_Pass, ymax=max_Pass), width=.2,linewidth = 0.3,position=position_dodge(.9), color = "gray60") +
#   geom_point(aes(y=avg_evalAt1), shape = 8, color=eval_col, size = 1.5, show.legend = F) +
#   facet_wrap(~Cond) +
#   scale_fill_manual(values = licence_col) +
#   scale_y_continuous(labels = percent) +
#   theme_se() +
#   theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
#   theme(legend.position = "top") +
#   ylab("Mean Pass Tests")
# 
# 
# pass_barplot
# ggsave(filename = pass_barplot_file, plot = pass_barplot, device = "pdf", width = 7.5, height = 3.5, units = "in", dpi = 300)


# 
# ggplot(task_data, aes(x = Model, y = p_valid, fill = `Open model`)) +
#   geom_boxplot(colour = "gray60", linewidth = 0.2, outlier.size = 0.5) +
#   geom_point(data = model_data, aes( y=avg_evalAt1), shape = 8, color=eval_col, size = 1, show.legend = F) +
#   #facet_wrap(~Cond) +
#   facet_wrap(~Cond, ncol=1) +
#   scale_fill_manual(values = licence_col) +
#   scale_y_continuous(labels = percent) +
#   theme_se() +
#   theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1), axis.title.x = element_blank()) +
#   theme(legend.position = "top", legend.box.spacing = unit(-5, units = "pt")  ) +
#   ylab("Valid Condition per Task")